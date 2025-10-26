"""Data models for tool parameters, results, and experiment traces."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


def _empty_grep_hits() -> list[GrepHit]:
    """Return an empty list for grep hits."""
    return []


def _empty_keyword_hits() -> list[KeywordHit]:
    """Return an empty list for keyword hits."""
    return []


def _empty_semantic_hits() -> list[SemanticHit]:
    """Return an empty list for semantic hits."""
    return []


def _empty_ast_findings() -> list[AstFinding]:
    """Return an empty list for AST findings."""
    return []


def _empty_find_items() -> list[FindItem]:
    """Return an empty list for fd results."""
    return []


def _empty_tool_calls() -> list[ToolCall]:
    """Return an empty list for tool calls."""
    return []


class ToolParam(BaseModel):
    """Base class for tool parameters."""


class ToolResult(BaseModel):
    """Base class for tool results."""

    ok: bool = True
    latency_ms: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)


class GrepParams(ToolParam):
    """Parameters for ripgrep-based search."""

    pattern: str
    root: str
    timeout_s: float | None = 30.0


class GrepHit(BaseModel):
    """Single grep hit with file context."""

    path: str
    line: int
    text: str


class GrepResult(ToolResult):
    """Result payload for grep searches."""

    hits: list[GrepHit] = Field(default_factory=_empty_grep_hits)


class KeywordParams(ToolParam):
    """Parameters for BM25 keyword search."""

    query: str
    root: str
    topk: int = 50


class KeywordHit(BaseModel):
    """Ranked document entry for keyword search."""

    path: str
    score: float


class KeywordResult(ToolResult):
    """Result payload for keyword search."""

    hits: list[KeywordHit] = Field(default_factory=_empty_keyword_hits)


class SemanticParams(ToolParam):
    """Parameters for semantic embedding search."""

    query: str
    root: str
    topk: int = 50


class SemanticHit(BaseModel):
    """Ranked document entry for semantic search."""

    path: str
    score: float


class SemanticResult(ToolResult):
    """Result payload for semantic search."""

    hits: list[SemanticHit] = Field(default_factory=_empty_semantic_hits)


class AstParams(ToolParam):
    """Parameters controlling AST inspection."""

    root: str
    symbol: str | None = None
    languages: list[str] = Field(default_factory=lambda: ["python"])
    scope_globs: list[str] | None = None


class AstFinding(BaseModel):
    """Single AST finding entry."""

    kind: Literal["def", "ref", "call", "note"]
    path: str
    line: int
    text: str


class AstResult(ToolResult):
    """Result payload for AST searches."""

    findings: list[AstFinding] = Field(default_factory=_empty_ast_findings)


class FindParams(ToolParam):
    """Parameters for fd-backed discovery."""

    root: str
    pattern: str | None = None
    type_filter: str | None = None


class FindItem(BaseModel):
    """Discovered path entry."""

    path: str


class FindResult(ToolResult):
    """Result payload for fd discovery."""

    items: list[FindItem] = Field(default_factory=_empty_find_items)


class ToolCall(BaseModel):
    """Trace entry for a single tool invocation."""

    name: str
    params: dict[str, Any]
    result_summary: dict[str, Any]
    latency_ms: int


class FlowTrace(BaseModel):
    """Aggregated execution trace for a run."""

    run_id: str
    calls: list[ToolCall] = Field(default_factory=_empty_tool_calls)
    metrics: dict[str, float] = Field(default_factory=dict)
