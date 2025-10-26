"""Tests for the ``lab tools`` CLI entry points."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest
from typer.testing import CliRunner

from codeagent_lab.cli import tools as tools_cli
from codeagent_lab.models import ToolParam, ToolResult


class _StubRegistry:
    """Simple mapping wrapper emulating ``ToolFactory`` access."""

    def __init__(self, mapping: dict[str, Any]) -> None:
        self._mapping = mapping

    def get(self, key: str) -> Any:
        return self._mapping[key]

    def items(self) -> list[tuple[str, Any]]:
        return list(self._mapping.items())


@dataclass
class _StubContainer:
    """Container stub exposing only the ``tools`` registry."""

    tools: _StubRegistry


class _DummyParam(ToolParam):
    """Parameters for the dummy echo tool."""

    message: str


class _DummyResult(ToolResult):
    """Result payload for the dummy echo tool."""

    echoed: str


class _EchoTool:
    """Tool implementation that echoes the provided message."""

    name = "echo"
    Param = _DummyParam
    Result = _DummyResult

    def __init__(self) -> None:
        self.calls: list[_DummyParam] = []

    def run(self, params: _DummyParam) -> _DummyResult:
        self.calls.append(params)
        return _DummyResult(echoed=params.message)

    @staticmethod
    def describe() -> str:
        return "Echo back the supplied message."

    @staticmethod
    def json_schema() -> dict[str, object]:  # pragma: no cover - compatibility shim
        return _DummyParam.model_json_schema()


@pytest.fixture
def runner() -> CliRunner:
    """Return a CLI runner for invoking Typer commands."""
    return CliRunner()


def test_run_executes_tool_and_prints_result(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """The ``run`` command validates parameters and outputs the tool result."""
    tool = _EchoTool()
    container = _StubContainer(_StubRegistry({"echo": tool}))
    monkeypatch.setattr(tools_cli, "build_container", lambda: container)

    result = runner.invoke(
        tools_cli.app,
        ["run", "--domain", "echo", "--params-json", json.dumps({"message": "hi"})],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["echoed"] == "hi"
    assert tool.calls
    assert tool.calls[0].message == "hi"


def test_run_unknown_domain_exits_with_error(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Unknown tool domains trigger a non-zero exit with a helpful message."""
    container = _StubContainer(_StubRegistry({}))
    monkeypatch.setattr(tools_cli, "build_container", lambda: container)

    result = runner.invoke(
        tools_cli.app,
        ["run", "--domain", "missing", "--params-json", "{}"],
    )

    assert result.exit_code == 1
    assert "Unknown tool domain" in result.output


def test_openai_spec_single_domain(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """The OpenAI spec command can limit output to a single domain."""
    tool = _EchoTool()
    container = _StubContainer(_StubRegistry({"echo": tool}))
    monkeypatch.setattr(tools_cli, "build_container", lambda: container)

    result = runner.invoke(
        tools_cli.app,
        ["openai-spec", "--domain", "echo"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"echo"}
    assert payload["echo"]["name"] == tool.name


def test_openai_spec_unknown_domain(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Requesting a missing domain exits with an explanatory error."""
    container = _StubContainer(_StubRegistry({}))
    monkeypatch.setattr(tools_cli, "build_container", lambda: container)

    result = runner.invoke(
        tools_cli.app,
        ["openai-spec", "--domain", "missing"],
    )

    assert result.exit_code == 1
    assert "Unknown tool domain" in result.output
