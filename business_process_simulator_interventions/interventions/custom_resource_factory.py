from simpy import Environment

from business_process_simulator_interventions.interventions.custom_resource import CustomResource


class CustomResourceFactory:
    @staticmethod
    def create_custom_resource(env: Environment, resource_name: str, capacity: int) -> CustomResource:
        cr = CustomResource(env, capacity)
        cr.name = resource_name
        return cr
