from random import uniform
from typing import List
from pm4py.objects.petri_net.obj import PetriNet

from business_process_simulator_interventions.data.gateway_info import GatewayInfo


def select_activity_gateway(g_info: GatewayInfo, all_enabled_trans: List[PetriNet.Transition]) -> PetriNet.Transition:
    trans_perc = g_info.percentages
    sum_percentages = sum(trans_perc.values())
    random_prob = uniform(0, sum_percentages)
    accum = 0
    selected_activity = None
    for trans, prob in trans_perc.items():
        accum += prob
        if random_prob <= accum:
            selected_activity = trans
            break

    return next(
        trans for trans in all_enabled_trans if trans.label == selected_activity or trans.name == selected_activity)
