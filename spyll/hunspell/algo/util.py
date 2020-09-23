from typing import Iterator, Tuple, TypeVar, Generic, List, Optional

Value = TypeVar('Value')


class ScoredArray(Generic[Value]):
    data: List[Tuple[Optional[Value], float]]

    def __init__(self, size: int):
        # FIXME: Can't guess how to do it with NamedTuple instead of tuple so mypy would
        # be happy :(
        self.data = [(None, -100*i) for i in range(size)]
        self.insert_at = size - 1

    def push(self, value: Value, score: float):
        if score <= self.data[self.insert_at][1]:
            return

        self.data[self.insert_at] = (value, score)

        # Next value should be inserted at the point which currently has minimum score
        # below current score
        lowest = score
        for i, cur in enumerate(self.data):
            if cur[1] < lowest:
                self.insert_at = i
                lowest = cur[1]

    def result(self) -> Iterator[Tuple[Value, float]]:
        # Mypy's unhappy...
        # return filter(lambda s: s[0], self.data)
        for value, score in self.data:
            if value:
                yield (value, score)
