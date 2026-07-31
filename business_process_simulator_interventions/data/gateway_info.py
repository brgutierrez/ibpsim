from typing import List, Dict, Tuple


class GatewayInfo:
    def __init__(self, gateway_id: str, sequences: List[Tuple[str, float]]):
        self.__gateway_id = gateway_id
        self.__sequences = sequences
        self.__percentages = self.__flat_sequences()
        self.__percentages_sum = sum(self.__percentages.values())

    @property
    def gateway_id(self) -> str:
        return self.__gateway_id

    @property
    def sequences(self) -> List[Tuple[str, float]]:
        return self.__sequences

    @property
    def percentages(self) -> Dict[str, float]:
        return self.__percentages

    @property
    def percentages_sum(self) -> float:
        return self.__percentages_sum

    @percentages.setter
    def percentages(self, new_percentages: Dict[str, float]) -> None:
        self.__percentages = new_percentages
        self.__percentages_sum = sum(new_percentages.values())
        self.__sequences = [(k, v) for k, v in new_percentages.items()]

    def __flat_sequences(self) -> Dict[str, float]:
        return {trans[0]: trans[1] for trans in self.__sequences}
