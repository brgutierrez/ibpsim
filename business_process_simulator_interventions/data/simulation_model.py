import os
import pm4py
from pm4py.objects.conversion.bpmn import converter as bpmn_converter
import pandas as pd
from collections import defaultdict
from typing import Dict, List

from business_process_simulator_interventions.data.gateway_info import GatewayInfo
from business_process_simulator_interventions.interventions.custom_resource import CustomResource


class ModelLogSimulation:
    def __init__(self, filepath: str, durations_filepath: str, resources_filepath: str, gateways_perc_filepath: str):
        self.__filepath = filepath
        self.__validate_file_path(filepath)
        self.__bpmn_model = None
        self.__net = None
        self.__petrinet = None
        self.__initial_marking = None
        self.__final_marking = None
        self.__activities = None
        self.__initialize_properties()

        self.__activities_duration = self.__load_durations(durations_filepath)
        self.__resources_distribution = self.__load_resources(resources_filepath)
        self.__resources_types = list(set(self.__resources_distribution.values()))
        self.__resources_object = {}
        self.__activities_percentages = self.__load_gateways_percentages(gateways_perc_filepath)

        self.__interventions_factory = None

    def __validate_file_path(self, filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The file {filepath} does not exist.")

    @property
    def filepath(self) -> str:
        return self.__filepath

    @property
    def bpmn_model(self):
        return self.__bpmn_model

    @property
    def net(self):
        return self.__net

    @property
    def petrinet(self):
        return self.__petrinet

    @property
    def initial_marking(self):
        return self.__initial_marking

    @property
    def final_marking(self):
        return self.__final_marking

    @property
    def activities(self) -> List[str]:
        return self.__activities

    @property
    def activities_duration(self) -> Dict[str, int]:
        return self.__activities_duration

    @activities_duration.setter
    def activities_duration(self, act_dur: Dict[str, int]):
        self.__activities_duration = act_dur

    def get_activity_duration(self, activity_name: str) -> int:
        return self.__activities_duration.get(activity_name)

    def set_activity_duration(self, activity_name: str, new_duration: int):
        self.__activities_duration[activity_name] = new_duration

    @property
    def resources_distribution(self) -> Dict[str, str]:
        return self.__resources_distribution

    @property
    def resources_types(self) -> List[str]:
        return self.__resources_types

    @property
    def activities_percentages(self) -> Dict[str, GatewayInfo]:
        return self.__activities_percentages

    @property
    def interventions_factory(self):
        return self.__interventions_factory

    @interventions_factory.setter
    def interventions_factory(self, interventions_user_info: Dict) -> Dict:
        self.__interventions_factory = interventions_user_info

    @property
    def resources_object(self):
        return self.__resources_object

    def add_resource(self, resource):
        if isinstance(resource, CustomResource):
            self.__resources_object[resource.name] = resource
        else:
            raise ValueError("Resource must be of type CustomResource")

    def __str__(self):
        return (f'ModelLogSimulation(filepath={self.__filepath}, bpmn_model={self.__bpmn_model}, net={self.__net}, '
                f'initial_marking={self.__initial_marking}, final_marking={self.__final_marking})')

    def __load_durations(self, durations_filepath: str) -> Dict[str, int]:
        self.__validate_file_path(durations_filepath)
        df_durations = pd.read_csv(durations_filepath)
        return {row['ACTIVITY'].strip(): int(row['DURATION']) for _, row in df_durations.iterrows()}

    def __load_resources(self, resources_filepath: str) -> Dict[str, str]:
        self.__validate_file_path(resources_filepath)
        df_resources = pd.read_csv(resources_filepath).dropna(subset=['RESOURCE'])
        return {row['ACTIVITY'].strip(): row['RESOURCE'].strip() for _, row in df_resources.iterrows()}

    def __load_gateways_percentages(self, gateways_perc_filepath: str) -> Dict[str, GatewayInfo]:
        self.__validate_file_path(gateways_perc_filepath)
        df_percentages = pd.read_csv(gateways_perc_filepath)
        activities_percentage = self.__parse_activities_percentage(df_percentages)

        gateway_places = self.__find_gateway_places()

        if not gateway_places and 'GATEWAY_ID' in df_percentages.columns:
            gateway_ids = df_percentages['GATEWAY_ID'].unique().tolist()
            gateway_places = self.__find_gateway_places_by_ids(gateway_ids)

        seqs_per_gateway_id, gateways_accum = self.__compute_gateways_sequences(gateway_places, activities_percentage)
        self.__balance_gateway_percentages(seqs_per_gateway_id, gateways_accum)

        return {k: GatewayInfo(k, v) for k, v in seqs_per_gateway_id.items()}

    def __parse_activities_percentage(self, df_percentages: pd.DataFrame) -> Dict[str, int]:
        return {row['ACTIVITY'].strip(): int(row['PERCENTAGE']) for _, row in df_percentages.iterrows() if
                pd.notna(row['ACTIVITY'])}

    def __find_gateway_places(self):
        return [place for place in self.__petrinet[0].places if 'Gateway' in place.name and len(place.out_arcs) > 1]

    def __find_gateway_places_by_ids(self, gateways_ids: List[str]):
        places_and_transitions = list(self.__petrinet[0].places).copy()
        places_and_transitions.extend(self.__petrinet[0].transitions)
        return [
            place for place in places_and_transitions
            if (
                       place.name in gateways_ids or  # Coincide con el nombre directamente
                       place.name.replace('exi_', '', 1) in gateways_ids or  # Coincide al eliminar 'exi_' una vez
                       place.name.replace('ent_', '', 1) in gateways_ids  # Coincide al eliminar 'ent_' una vez
               ) and len(place.out_arcs) > 1
        ]

    def __compute_gateways_sequences(self, gateway_places, activities_percentage: Dict[str, int]):
        seqs_per_gateway_id = defaultdict(list)
        gateways_accum = defaultdict(int)
        for g in gateway_places:
            gateway_id = g.name
            gateway_seqs = []
            for arc in g.out_arcs:
                trans_label = arc.target.label if arc.target.label else arc.target.name
                percen = activities_percentage.get(trans_label, 0)
                gateway_seqs.append([trans_label, percen])
                gateways_accum[gateway_id] += percen
            seqs_per_gateway_id[gateway_id] = gateway_seqs
        return seqs_per_gateway_id, gateways_accum

    def __balance_gateway_percentages(self, seqs_per_gateway_id, gateways_accum):
        for g, accum in gateways_accum.items():
            if accum != 100:
                rest = 100 - accum
                for trans in seqs_per_gateway_id[g]:
                    if trans[1] == 0:
                        trans[1] = rest

    def __initialize_properties(self):
        bpmn_graph = pm4py.read_bpmn(self.__filepath)
        self.__bpmn_model = bpmn_graph

        self.__petrinet = pm4py.convert.convert_to_petri_net(bpmn_graph)

        activities = [act.name for act in list(bpmn_graph.get_nodes()) if
                      isinstance(act, pm4py.objects.bpmn.obj.BPMN.Task)]
        self.__activities = activities

        net, im, fm = bpmn_converter.apply(bpmn_graph)
        self.__net = net
        self.__initial_marking = im
        self.__final_marking = fm
