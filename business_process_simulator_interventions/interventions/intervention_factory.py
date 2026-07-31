from datetime import datetime
from typing import List, Tuple, Dict

import simpy

from business_process_simulator_interventions.data.simulation_model import ModelLogSimulation
from business_process_simulator_interventions.interventions.custom_resource_factory import CustomResourceFactory
from business_process_simulator_interventions.interventions.resource_capacity_intervention import \
    ResourceCapacityIntervention
from business_process_simulator_interventions.interventions.activity_duration_intervention import \
    ActivityDurationIntervention
from business_process_simulator_interventions.interventions.gateway_percentage_intervention import \
    GatewayPercentageIntervention


class InterventionsFactory:

    def __init__(self, intervention_data: Dict[str, Dict]):
        self.__date_to_plan = None
        self.__interventions_to_launch = []
        self.__resource_info = intervention_data.get('resource_intervention_info', {})
        self.__activity_info = intervention_data.get('activity_intervention_info', {})
        self.__percentage_info = intervention_data.get('percentage_intervention_info', {})
        self.__resources_intervention_date = intervention_data.get('resources_intervention_date')
        self.__activities_intervention_date = intervention_data.get('activities_intervention_date')
        self.__percentages_intervention_date = intervention_data.get('percentages_intervention_date')
        self.__resource_interventions = None
        self.__activity_interventions = None
        self.__percentage_interventions = None
        self.__env = None
        self.__modellogsimul = None

    @property
    def resource_info(self) -> Dict:
        return self.__resource_info

    @property
    def activity_info(self) -> Dict:
        return self.__activity_info

    @property
    def percentage_info(self) -> Dict:
        return self.__percentage_info

    @property
    def resource_interventions(self) -> List[ResourceCapacityIntervention]:
        return self.__resource_interventions

    @property
    def activity_interventions(self) -> List[ActivityDurationIntervention]:
        return self.__activity_interventions

    @property
    def percentage_interventions(self) -> List[GatewayPercentageIntervention]:
        return self.__percentage_interventions

    @property
    def interventions_to_launch(self):
        return self.__interventions_to_launch

    def create_all_interventions(self, env: simpy.Environment, modellogsimul: ModelLogSimulation, date_to_plan_dt):
        self.__env = env
        self.__modellogsimul = modellogsimul
        self.__date_to_plan = date_to_plan_dt.date()
        resource_interventions = self.create_resource_interventions(self.__resource_info)
        activity_interventions = self.create_activity_interventions(self.__activity_info)
        percentage_interventions = self.create_percentage_interventions(self.__percentage_info)
        self.__resource_interventions = resource_interventions
        self.__activity_interventions = activity_interventions
        self.__percentage_interventions = percentage_interventions

        if not self.__modellogsimul.resources_object:
            self.__populate_resources()

    def __populate_resources(self):
        for resource, data in self.__resource_info.items():
            initial_capacity = data.get('initial')
            model_resource = CustomResourceFactory.create_custom_resource(self.__env, resource, initial_capacity)
            self.__modellogsimul.add_resource(model_resource)

    def create_resource_interventions(self, resource_info: dict) -> List[ResourceCapacityIntervention]:

        if self.__date_to_plan >= self.__resources_intervention_date:
            for resource, data in resource_info.items():
                if resource not in self.__modellogsimul.resources_object:
                    initial_count = data.get('initial')
                    modified_count = data.get('modified')
                    change_time = data.get('change_time')

                    if modified_count is not None:
                        intervention = ResourceCapacityIntervention(env=self.__env, model_resource=resource,
                                                                    initial_capacity=initial_count,
                                                                    new_capacity=modified_count,
                                                                    changing_moment=change_time,
                                                                    modellogsimul=self.__modellogsimul,
                                                                    simulation_day=self.__date_to_plan,
                                                                    intervention_date=self.__resources_intervention_date
                                                                    )

                        self.__interventions_to_launch.append(intervention)
                else:
                    initial_count = self.__modellogsimul.resources_object[resource].capacity
                    modified_count = modified_count = data.get('modified')
                    change_time = data.get('change_time')
                    intervention = ResourceCapacityIntervention(env=self.__env, model_resource=resource,
                                                                initial_capacity=initial_count,
                                                                new_capacity=modified_count,
                                                                changing_moment=change_time,
                                                                modellogsimul=self.__modellogsimul,
                                                                simulation_day=self.__date_to_plan,
                                                                intervention_date=self.__resources_intervention_date
                                                                )

                    self.__interventions_to_launch.append(intervention)

    def create_activity_interventions(self, activity_info: dict) -> List[ActivityDurationIntervention]:
        if self.__date_to_plan >= self.__activities_intervention_date:
            for activity, data in activity_info.items():
                new_duration = data.get('new_duration')
                change_time = data.get('change_time')

                if new_duration is not None:
                    intervention = ActivityDurationIntervention(env=self.__env, modellogsimul=self.__modellogsimul,
                                                                activity_name=activity,
                                                                new_duration=new_duration,
                                                                changing_moment=change_time,
                                                                simulation_day=self.__date_to_plan,
                                                                intervention_date=self.__activities_intervention_date)

                    self.__interventions_to_launch.append(intervention)

    def create_percentage_interventions(self, percentage_info: dict) -> List[GatewayPercentageIntervention]:

        if self.__date_to_plan >= self.__percentages_intervention_date:
            for gateway_id, percentage_intervention in percentage_info.items():

                change_time = percentage_intervention.get('change_time')

                if change_time is not None:
                    new_percentages = percentage_intervention.get('percentages')

                    intervention = GatewayPercentageIntervention(env=self.__env, modellogsimul=self.__modellogsimul,
                                                                 gateway_id=gateway_id,
                                                                 new_percentages=new_percentages,
                                                                 changing_moment=change_time,
                                                                 simulation_day=self.__date_to_plan,
                                                                 intervention_date=self.__percentages_intervention_date)

                    self.__interventions_to_launch.append(intervention)
