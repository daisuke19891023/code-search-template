"""fd-based file discovery placeholder."""

from __future__ import annotations

from codeagent_lab.models import FindParams, FindResult
from codeagent_lab.tools.protocols import Tool


class FdTool(Tool[FindParams, FindResult]):
    """Placeholder for fd-backed discovery."""

    name = "find.fd"
    Param = FindParams
    Result = FindResult

    def run(self, params: FindParams) -> FindResult:
        """Execute fd search (not implemented in the template)."""
        message = "FdTool.run is not implemented yet"
        raise NotImplementedError(message)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "List files using fd."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()
