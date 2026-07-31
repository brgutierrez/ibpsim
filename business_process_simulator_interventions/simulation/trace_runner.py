from copy import copy
import simpy
from pm4py.objects.petri_net import semantics
from typing import Dict, List

from datetime import datetime

from .activity_execution import execute_activity
from .activity_selection import select_activity_gateway
from ..interventions.custom_resource import CustomResource
from ..data.simulation_model import ModelLogSimulation
from ..data.shipcall_info import ShipcallInfo


def trace_runner(env: simpy.Environment, trace_id: int, model_resources: Dict[str, CustomResource],
                 modellogsimul: ModelLogSimulation, waiting_activity: str, sh: ShipcallInfo, date_to_plan: datetime,
                 results_log: List[List[str]], arrival_or_departure: int):
    marking = copy(modellogsimul.initial_marking)
    while semantics.enabled_transitions(modellogsimul.net, marking):
        all_enabled_trans = list(semantics.enabled_transitions(modellogsimul.net, marking))
        if len(all_enabled_trans) > 1:
            gateway_name = list(marking.keys())[0].name
            g_info = modellogsimul.activities_percentages[gateway_name]
            trans = select_activity_gateway(g_info, all_enabled_trans)
        else:
            trans = all_enabled_trans[0]

        if trans.label:
            yield env.process(
                execute_activity(env, trans.label, model_resources, modellogsimul, trace_id, waiting_activity,
                                 sh, date_to_plan, results_log, arrival_or_departure))
        marking = semantics.execute(trans, modellogsimul.net, marking)
