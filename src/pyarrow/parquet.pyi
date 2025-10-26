
from typing import Any

from . import Table


def write_table(
    table: Table,
    where: str,
    /,
    *,
    compression: str | None = ...,
    **kwargs: Any,
) -> None: ...
