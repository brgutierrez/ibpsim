from simpy import Resource


class CustomResource(Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._capacity = self.capacity
        self._name = None

    @property
    def capacity(self) -> int:
        return self._capacity

    @capacity.setter
    def capacity(self, new_capacity: int):
        self._capacity = new_capacity

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str = 'default_name'):
        self._name = new_name

    def __str__(self) -> str:
        return f"{self._name}: capacity={self._capacity}"

    def print_usage(self) -> None:
        print('---------------------------------------------------------------------' * 2)
        print(f"{self._name}: capacity={self._capacity}")
        print(f"Busy: {self.count}")
        print(f"Free: {self.capacity - self.count}")
        print('---------------------------------------------------------------------' * 2)

    def print_usage_conditional(self, date: str, act: str, trace_id: str, simtime: float) -> None:
        if self.capacity - self.count == 0:
            print('---------------------------------------------------------------------' * 2)
            print(date)
            print(trace_id, act)
            print(simtime)
            print(f"{self._name}: capacity={self._capacity}")
            print(f"Busy: {self.count}")
            print(f"Free: {self.capacity - self.count}")
            print('---------------------------------------------------------------------' * 2)
