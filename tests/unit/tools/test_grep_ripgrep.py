"""Tests for the ripgrep-backed tool."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from codeagent_lab.models import GrepParams
from codeagent_lab.tools.grep_ripgrep import RipgrepTool

if TYPE_CHECKING:
    from pathlib import Path


def _create_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip the test when unsupported."""
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks not supported: {exc}")


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


def test_ripgrep_tool_ignores_symlinks_outside_root(tmp_path: Path) -> None:
    """Files reached via symlinks outside the root are ignored."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "sample.txt").write_text("TODO: write more tests\n")

    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_file = external_dir / "secret.txt"
    external_file.write_text("TODO: ignore this\n")

    link = repo_root / "linked.txt"
    _create_symlink(link, external_file)

    tool = RipgrepTool()
    params = GrepParams(pattern="TODO", root=str(repo_root))

    result = tool.run(params)

    assert result.ok is True
    paths = {hit.path for hit in result.hits}
    assert "sample.txt" in paths
    assert "linked.txt" not in paths
