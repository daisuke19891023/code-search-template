"""Tests for the LLM tool adapter."""

from __future__ import annotations

from codeagent_lab.llm.tools_adapter import tool_to_openai_spec
from codeagent_lab.models import ToolParam, ToolResult


class _AdapterParams(ToolParam):
    value: int


class _AdapterResult(ToolResult):
    message: str = "ok"


class _DummyTool:
    name = "dummy"
    Param = _AdapterParams
    Result = _AdapterResult

    def run(self, params: _AdapterParams) -> _AdapterResult:
        raise NotImplementedError

    def describe(self) -> str:
        return "Dummy tool for testing."

    def json_schema(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "value": {"type": "integer", "description": "A numeric value."},
            },
            "required": ["value"],
        }


def test_tool_to_openai_spec_builds_function_schema() -> None:
    """Produce an OpenAI function schema for the tool."""
    tool = _DummyTool()

    spec = tool_to_openai_spec(tool)

    assert spec == {
        "type": "function",
        "function": {
            "name": "dummy",
            "description": "Dummy tool for testing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "integer", "description": "A numeric value."},
                },
                "required": ["value"],
            },
        },
    }
