"""Adapters for exposing tools to LLM function calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codeagent_lab.tools.protocols import Tool


def tool_to_openai_spec(tool: Tool) -> dict[str, Any]:
    """Convert a tool into an OpenAI function tool schema."""
    schema = tool.Param.model_json_schema()
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.describe(),
            "parameters": schema,
        },
    }
