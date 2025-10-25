"""Protocols describing the tool interface."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

from codeagent_lab.models import ToolParam, ToolResult

P = TypeVar("P", bound=ToolParam)
R = TypeVar("R", bound=ToolResult)


class Tool(Protocol, Generic[P, R]):
    """Protocol representing a synchronous tool."""

    name: str
    Param: type[P]
    Result: type[R]

    def run(self, params: P) -> R:
        """Execute the tool using the provided parameters."""

        ...

    def describe(self) -> str:
        """Return a human-readable description of the tool."""

        ...

    def json_schema(self) -> dict[str, object]:
        """Return a JSON schema describing the parameters."""

        ...
