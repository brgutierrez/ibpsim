import simpy

from business_process_simulator_interventions.data.simulation_model import ModelLogSimulation
from business_process_simulator_interventions.interventions.base_intevention import BaseIntervention


class ActivityDurationIntervention(BaseIntervention):
    def __init__(self, env: simpy.Environment, modellogsimul: ModelLogSimulation, activity_name: str, new_duration: int,
                 changing_moment: int, simulation_day, intervention_date):
        super().__init__(env, modellogsimul)
        self.activity_name = activity_name
        self.new_duration = new_duration
        self.changing_moment = changing_moment
        self.__simulation_day = simulation_day
        self.__intervention_date = intervention_date

    def execute(self):
        if self.__simulation_day >= self.__intervention_date:
            yield self.env.timeout(self.changing_moment)
            print('---------------------------------------------------------------------' * 2)
            print(
                f'{self.env.now}: Changing activity {self.activity_name} duration from '
                f'{self.modellogsimul.get_activity_duration(self.activity_name)} to {self.new_duration}')
            print('---------------------------------------------------------------------' * 2)
            self.modellogsimul.set_activity_duration(self.activity_name, self.new_duration)
