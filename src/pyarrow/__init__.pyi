
from collections.abc import Mapping, Sequence

class Table:
    @classmethod
    def from_pylist(cls, data: Sequence[Mapping[str, object]]) -> Table: ...

