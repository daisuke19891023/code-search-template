"""Ripgrep-based tool placeholder."""

from __future__ import annotations

from codeagent_lab.models import GrepParams, GrepResult
from codeagent_lab.tools.protocols import Tool


class RipgrepTool(Tool[GrepParams, GrepResult]):
    """Placeholder implementation for the ripgrep-backed search."""

    name = "grep.ripgrep"
    Param = GrepParams
    Result = GrepResult

    def run(self, params: GrepParams) -> GrepResult:
        """Execute ripgrep search (not implemented in the template)."""
        message = "RipgrepTool.run is not implemented yet"
        raise NotImplementedError(message)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Search files using ripgrep."

    def json_schema(self) -> dict:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()
