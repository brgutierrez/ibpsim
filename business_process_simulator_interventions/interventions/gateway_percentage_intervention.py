import simpy

from business_process_simulator_interventions.data.simulation_model import ModelLogSimulation
from business_process_simulator_interventions.interventions.base_intevention import BaseIntervention


class GatewayPercentageIntervention(BaseIntervention):
    def __init__(self, env: simpy.Environment, modellogsimul: ModelLogSimulation, gateway_id: str,
                 new_percentages: dict[str, int], changing_moment: int, simulation_day, intervention_date):
        super().__init__(env, modellogsimul)
        self.gateway_id = gateway_id
        self.new_percentages = new_percentages
        self.changing_moment = changing_moment
        self.__simulation_day = simulation_day
        self.__intervention_date = intervention_date

    def execute(self):
        if self.__simulation_day >= self.__intervention_date:
            yield self.env.timeout(self.changing_moment)
            print('---------------------------------------------------------------------' * 2)
            print(
                f'{self.env.now}: Changing gateway {self.gateway_id} percentages from '
                f'{self.modellogsimul.activities_percentages[self.gateway_id].percentages} to {self.new_percentages}')
            print('---------------------------------------------------------------------' * 2)
            self.modellogsimul.activities_percentages[self.gateway_id].percentages = self.new_percentages
