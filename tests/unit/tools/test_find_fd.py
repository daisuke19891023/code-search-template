"""Tests for the fd-inspired discovery tool."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from codeagent_lab.models import FindParams
from codeagent_lab.tools.find_fd import FdTool

if TYPE_CHECKING:
    from pathlib import Path


def _create_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip the test when unsupported."""
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks not supported: {exc}")


def test_fd_tool_filters_by_pattern(tmp_path: Path) -> None:
    """Entries must match the provided regex pattern."""
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "keep_match.txt").write_text("content\n")
    (nested / "ignore.log").write_text("log\n")

    tool = FdTool()
    params = FindParams(root=str(tmp_path), pattern=r"match\.txt$")

    result = tool.run(params)

    paths = {item.path for item in result.items}
    assert result.ok is True
    assert paths == {"nested/keep_match.txt"}


def test_fd_tool_type_filter_files_only(tmp_path: Path) -> None:
    """When ``type_filter`` is ``file`` directories are excluded."""
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "file.txt").write_text("content\n")

    tool = FdTool()
    params = FindParams(root=str(tmp_path), type_filter="file")

    result = tool.run(params)

    assert result.ok is True
    assert {item.path for item in result.items} == {"nested/file.txt"}


def test_fd_tool_rejects_unknown_type(tmp_path: Path) -> None:
    """Unsupported type filters return an error result."""
    (tmp_path / "file.txt").write_text("content\n")

    tool = FdTool()
    params = FindParams(root=str(tmp_path), type_filter="symlink")

    result = tool.run(params)

    assert result.ok is False
    assert result.meta["error"] == "invalid-type"


def test_fd_tool_ignores_symlinks_outside_root(tmp_path: Path) -> None:
    """Entries reached via symlinks outside the root are skipped."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "inside.txt").write_text("content\n")

    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_file = external_dir / "outside.txt"
    external_file.write_text("secret\n")

    _create_symlink(repo_root / "link.txt", external_file)

    tool = FdTool()
    params = FindParams(root=str(repo_root))

    result = tool.run(params)

    assert result.ok is True
    paths = {item.path for item in result.items}
    assert paths == {"inside.txt"}
