from datetime import datetime

import simpy

from business_process_simulator_interventions.data.simulation_model import ModelLogSimulation
from business_process_simulator_interventions.interventions.base_intevention import BaseIntervention
from business_process_simulator_interventions.interventions.custom_resource import CustomResource
from business_process_simulator_interventions.interventions.custom_resource_factory import CustomResourceFactory


class ResourceCapacityIntervention(BaseIntervention):

    def __init__(self, env: simpy.Environment, model_resource: str,
                 initial_capacity: int, new_capacity: int, changing_moment: int, modellogsimul: ModelLogSimulation,
                 simulation_day, intervention_date):
        super().__init__(env, modellogsimul)
        self.model_resource = CustomResourceFactory.create_custom_resource(env, model_resource, initial_capacity)
        self.modellogsimul.add_resource(self.model_resource)
        self.new_capacity = new_capacity
        self.changing_moment = changing_moment
        self.__simulation_day = simulation_day
        self.__intervention_date = intervention_date

    def execute(self) -> None:
        if self.__simulation_day >= self.__intervention_date:
            yield self.env.timeout(self.changing_moment)
            old_capacity = self.model_resource.capacity
            self.model_resource.print_usage()
            self.model_resource.capacity = self.new_capacity
            print(f'{self.env.now}: Changing resource capacity from {old_capacity} to {self.new_capacity}')
            self.model_resource.print_usage()
