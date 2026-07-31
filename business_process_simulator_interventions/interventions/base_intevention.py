from abc import ABC, abstractmethod
from simpy import Environment


class BaseIntervention(ABC):
    def __init__(self, env: Environment, modellogsimul):
        self.env = env
        self.modellogsimul = modellogsimul

    @abstractmethod
    def execute(self) -> None:
        pass
