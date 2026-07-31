from typing import List

from business_process_simulator_interventions.interventions.base_intevention import BaseIntervention


def interventions_launcher(interventions: List[BaseIntervention]) -> None:
    for intervention in interventions:
        intervention.env.process(intervention.execute())
