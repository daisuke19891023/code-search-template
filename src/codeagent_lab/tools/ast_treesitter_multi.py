"""Tree-sitter based AST tool placeholder."""

from __future__ import annotations

from codeagent_lab.models import AstParams, AstResult
from codeagent_lab.tools.protocols import Tool


class TreeSitterTool(Tool[AstParams, AstResult]):
    """Placeholder AST walker leveraging tree-sitter."""

    name = "ast.tree_sitter"
    Param = AstParams
    Result = AstResult

    def __init__(self, provider: object, queries: dict[str, dict[str, str]]) -> None:
        """Initialise the tree-sitter tool with providers and queries."""
        self._provider = provider
        self._queries = queries

    def run(self, params: AstParams) -> AstResult:
        """Execute AST analysis (not implemented in the template)."""
        message = "TreeSitterTool.run is not implemented yet"
        raise NotImplementedError(message)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Inspect syntax trees using tree-sitter."

    def json_schema(self) -> dict:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()
