"""Semantic search tool placeholder."""

from __future__ import annotations

from codeagent_lab.models import SemanticParams, SemanticResult
from codeagent_lab.tools.protocols import Tool


class SemanticOpenAITool(Tool[SemanticParams, SemanticResult]):
    """Placeholder for the semantic search pipeline."""

    name = "semantic.openai"
    Param = SemanticParams
    Result = SemanticResult

    def __init__(self, embedder: object, index: object, index_root: str) -> None:
        """Initialise the semantic tool with dependencies."""
        self._embedder = embedder
        self._index = index
        self._index_root = index_root

    def run(self, params: SemanticParams) -> SemanticResult:
        """Execute semantic search (not implemented in the template)."""
        message = "SemanticOpenAITool.run is not implemented yet"
        raise NotImplementedError(message)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Search using embeddings and a vector index."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()
