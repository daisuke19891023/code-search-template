"""Registry and factory helpers for tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeagent_lab.tools.protocols import Tool


@dataclass
class ToolFactory:
    """Simple registry mapping domains to tool instances."""

    registry: dict[str, Tool] = field(default_factory=dict)

    def register(self, domain: str, tool: Tool) -> None:
        """Register a tool instance under a domain name."""
        self.registry[domain] = tool

    def get(self, domain: str) -> Tool:
        """Retrieve a tool by domain name."""
        return self.registry[domain]

    def all(self) -> list[Tool]:
        """Return all registered tools."""
        return list(self.registry.values())
