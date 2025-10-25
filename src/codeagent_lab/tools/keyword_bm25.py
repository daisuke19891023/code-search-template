"""BM25 keyword search placeholder."""

from __future__ import annotations

from codeagent_lab.models import KeywordParams, KeywordResult
from codeagent_lab.tools.protocols import Tool


class KeywordBM25Tool(Tool[KeywordParams, KeywordResult]):
    """Placeholder implementation for keyword search."""

    name = "keyword.bm25"
    Param = KeywordParams
    Result = KeywordResult

    def run(self, params: KeywordParams) -> KeywordResult:
        """Execute BM25 ranking (not implemented in the template)."""
        message = "KeywordBM25Tool.run is not implemented yet"
        raise NotImplementedError(message)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Rank files using BM25 keyword scoring."

    def json_schema(self) -> dict:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()
