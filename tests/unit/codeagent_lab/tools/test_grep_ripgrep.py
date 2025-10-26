"""Tests for :mod:`codeagent_lab.tools.grep_ripgrep`."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING
from unittest.mock import Mock

from codeagent_lab.models import GrepParams
from codeagent_lab.tools.grep_ripgrep import RipgrepTool

if TYPE_CHECKING:
    from pathlib import Path
    import pytest


class _DummyProcess:
    """A lightweight stand-in for ``subprocess.Popen`` in tests."""

    def __init__(self, stdout_data: str, stderr_data: str = "", returncode: int = 0) -> None:
        self.stdout = io.StringIO(stdout_data)
        self.stderr = io.StringIO(stderr_data)
        self.stdin = io.StringIO()
        self.returncode = returncode

    def wait(self, _timeout: float | None = None) -> int:  # pragma: no cover - passthrough
        return self.returncode

    def kill(self) -> None:  # pragma: no cover - passthrough
        return


def _build_json_lines() -> str:
    return """\
{"type":"begin","data":{"path":{"text":"."}}}
{"type":"match","data":{"path":{"text":"sample.txt"},"lines":{"text":"hello world\\n"},"line_number":1}}
{"type":"summary","data":{"elapsed_total":{"human":"0.001s","nanos":1000000}}}
{"type":"end","data":{}}
"""


def test_run_streams_ripgrep_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Ripgrep output is parsed into ``GrepHit`` instances."""
    (tmp_path / "sample.txt").write_text("hello world\n")
    tool = RipgrepTool()

    dummy_process = _DummyProcess(stdout_data=_build_json_lines())

    monkeypatch.setattr(
        "codeagent_lab.tools.grep_ripgrep.Popen",
        Mock(return_value=dummy_process),
    )
    monkeypatch.setattr(
        tool,
        "_python_search",
        Mock(side_effect=AssertionError("python fallback should not run")),
    )

    result = tool.run(GrepParams(pattern="hello", root=str(tmp_path)))

    assert result.ok is True
    assert [hit.path for hit in result.hits] == ["sample.txt"]
    assert [hit.line for hit in result.hits] == [1]
    assert result.meta["executor"] == "ripgrep"
    assert result.meta["matches"] == 1
    assert result.meta["exit_code"] == 0
    assert result.meta["pattern"] == "hello"
    assert "summary" in result.meta


def test_run_falls_back_when_ripgrep_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """The tool falls back to the Python implementation when ``rg`` is missing."""
    (tmp_path / "fallback.txt").write_text("needle\n")
    tool = RipgrepTool()

    monkeypatch.setattr(
        "codeagent_lab.tools.grep_ripgrep.Popen",
        Mock(side_effect=FileNotFoundError()),
    )

    result = tool.run(GrepParams(pattern="needle", root=str(tmp_path)))

    assert result.ok is True
    assert [hit.path for hit in result.hits] == ["fallback.txt"]
    assert result.meta["executor"] == "python-fallback"
    assert result.meta["fallback_reason"]["error"] == "ripgrep-missing"
    assert "rg executable not found" in result.meta["fallback_reason"]["message"]
