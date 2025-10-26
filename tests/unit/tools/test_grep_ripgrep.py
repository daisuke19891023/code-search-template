"""Tests for the ripgrep-backed tool."""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeagent_lab.models import GrepParams
from codeagent_lab.tools.grep_ripgrep import RipgrepTool

if TYPE_CHECKING:
    from pathlib import Path


def test_ripgrep_tool_finds_matches(tmp_path: Path) -> None:
    """Ripgrep returns hits when the pattern exists."""
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("TODO: write more tests\n")

    tool = RipgrepTool()
    params = GrepParams(pattern="TODO", root=str(tmp_path))

    result = tool.run(params)

    assert result.ok is True
    assert any(hit.path.endswith("sample.txt") for hit in result.hits)
    assert all("TODO" in hit.text for hit in result.hits)


def test_ripgrep_tool_handles_no_matches(tmp_path: Path) -> None:
    """Ripgrep succeeds with no hits when pattern missing."""
    (tmp_path / "sample.txt").write_text("just some text\n")

    tool = RipgrepTool()
    params = GrepParams(pattern="TODO", root=str(tmp_path))

    result = tool.run(params)

    assert result.ok is True
    assert result.hits == []
    assert result.meta["exit_code"] == 1
