"""Tests for the ``lab-vdb`` CLI commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest
from typer.testing import CliRunner

from codeagent_lab.cli import vectordb as vectordb_cli
from codeagent_lab.models import SemanticHit, SemanticParams, SemanticResult


class _StubRegistry:
    """Simple mapping wrapper to emulate the tool factory."""

    def __init__(self, mapping: dict[str, Any]) -> None:
        self._mapping = mapping

    def get(self, key: str) -> Any:
        return self._mapping[key]


@dataclass
class _StubContainer:
    """Container stub exposing the ``tools`` registry."""

    tools: _StubRegistry


class _SemanticTool:
    """Semantic tool stub returning pre-configured results."""

    name = "semantic"
    Param = SemanticParams
    Result = SemanticResult

    def __init__(self, result: SemanticResult) -> None:
        self._result = result
        self.calls: list[SemanticParams] = []

    def run(self, params: SemanticParams) -> SemanticResult:
        self.calls.append(params)
        return self._result

    @staticmethod
    def describe() -> str:  # pragma: no cover - not used in tests
        return "semantic"

    @staticmethod
    def json_schema() -> dict[str, object]:  # pragma: no cover - compatibility shim
        return SemanticParams.model_json_schema()


@pytest.fixture
def runner() -> CliRunner:
    """Return a Typer CLI runner."""
    return CliRunner()


def test_build_reports_index_status(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """The build command reports whether the index was rebuilt."""
    result_payload = SemanticResult(
        hits=[],
        latency_ms=12,
        meta={"index": {"path": "/lab/index", "built": True}, "documents": 5},
    )
    tool = _SemanticTool(result_payload)
    container = _StubContainer(_StubRegistry({"semantic": tool}))
    monkeypatch.setattr(vectordb_cli, "build_container", lambda: container)

    result = runner.invoke(
        vectordb_cli.app,
        ["build", "--root", "."],
    )

    assert result.exit_code == 0
    assert "Index built at /lab/index (5 documents indexed)" in result.stdout
    assert tool.calls
    assert tool.calls[0].root == "."


def test_build_without_semantic_tool_exits(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """When the semantic tool is missing the command exits with an error."""
    container = _StubContainer(_StubRegistry({}))
    monkeypatch.setattr(vectordb_cli, "build_container", lambda: container)

    result = runner.invoke(
        vectordb_cli.app,
        ["build", "--root", "."],
    )

    assert result.exit_code == 1
    assert "Semantic tool is not configured" in result.output


def test_build_failure_surface_error_message(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Failures reported by the semantic tool propagate to the CLI."""
    result_payload = SemanticResult(
        ok=False,
        hits=[],
        meta={"error": "root-missing"},
    )
    tool = _SemanticTool(result_payload)
    container = _StubContainer(_StubRegistry({"semantic": tool}))
    monkeypatch.setattr(vectordb_cli, "build_container", lambda: container)

    result = runner.invoke(
        vectordb_cli.app,
        ["build", "--root", "."],
    )

    assert result.exit_code == 1
    assert "root-missing" in result.output


def test_search_outputs_hits(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """The search command prints the serialized semantic result."""
    result_payload = SemanticResult(
        hits=[SemanticHit(path="README.md", score=0.42)],
        latency_ms=7,
        meta={"index": {"path": "/lab/index", "built": False}, "documents": 1},
    )
    tool = _SemanticTool(result_payload)
    container = _StubContainer(_StubRegistry({"semantic": tool}))
    monkeypatch.setattr(vectordb_cli, "build_container", lambda: container)

    result = runner.invoke(
        vectordb_cli.app,
        ["search", "--query", "auth", "--root", ".", "--topk", "5"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["hits"][0]["path"] == "README.md"
    assert tool.calls
    assert tool.calls[0].query == "auth"


def test_search_failure_surface_error(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Search failures emit a helpful error message and non-zero exit."""
    result_payload = SemanticResult(ok=False, hits=[], meta={"error": "index-missing"})
    tool = _SemanticTool(result_payload)
    container = _StubContainer(_StubRegistry({"semantic": tool}))
    monkeypatch.setattr(vectordb_cli, "build_container", lambda: container)

    result = runner.invoke(
        vectordb_cli.app,
        ["search", "--query", "auth"],
    )

    assert result.exit_code == 1
    assert "index-missing" in result.output


def test_build_container_value_error(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Container validation errors produce a user-facing failure."""

    def _raise_value_error() -> None:
        raise ValueError("missing api key")

    monkeypatch.setattr(vectordb_cli, "build_container", _raise_value_error)

    result = runner.invoke(
        vectordb_cli.app,
        ["build", "--root", "."],
    )

    assert result.exit_code == 1
    assert "Failed to initialize container: missing api key" in result.output
