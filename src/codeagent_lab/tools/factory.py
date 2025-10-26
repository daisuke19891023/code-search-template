"""Registry and factory helpers for tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from codeagent_lab.models import ToolParam, ToolResult
from codeagent_lab.tools.protocols import Tool

ToolLike = Tool[ToolParam, ToolResult]
ToolAny = Tool[Any, Any]


def _empty_registry() -> dict[str, ToolLike]:
    """Create an empty tool registry."""
    return {}


@dataclass
class ToolFactory:
    """Simple registry mapping domains to tool instances."""

    registry: dict[str, ToolLike] = field(default_factory=_empty_registry)

    def register(self, domain: str, tool: ToolAny) -> None:
        """Register a tool instance under a domain name."""
        self.registry[domain] = cast("ToolLike", tool)

    def get(self, domain: str) -> ToolLike:
        """Retrieve a tool by domain name."""
        return self.registry[domain]

    def all(self) -> list[ToolLike]:
        """Return all registered tools."""
        return list(self.registry.values())

    def items(self) -> list[tuple[str, ToolLike]]:
        """Return ``(domain, tool)`` pairs for registered tools."""
        return list(self.registry.items())
