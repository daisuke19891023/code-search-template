"""Tests for the BM25 keyword search tool."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from codeagent_lab.models import KeywordParams
from codeagent_lab.tools.keyword_bm25 import KeywordBM25Tool

if TYPE_CHECKING:
    from pathlib import Path


def _create_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip the test when unsupported."""
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks not supported: {exc}")


def test_keyword_bm25_ranks_relevant_files(tmp_path: Path) -> None:
    """The most relevant file for the query appears first."""
    (tmp_path / "alpha.txt").write_text("Sorting numbers in ascending order.\n")
    (tmp_path / "beta.txt").write_text("Utility helpers for configuration loading.\n")
    (tmp_path / "ranking.txt").write_text(
        "BM25 ranking algorithms score documents for keyword search. Ranking is repeated.\n",
    )

    tool = KeywordBM25Tool()
    params = KeywordParams(query="ranking search algorithm", root=str(tmp_path), topk=3)

    result = tool.run(params)

    assert result.ok is True
    assert result.hits
    assert result.hits[0].path == "ranking.txt"
    assert result.hits[0].score > 0


def test_keyword_bm25_honors_topk(tmp_path: Path) -> None:
    """Top-k parameter limits the number of returned hits."""
    (tmp_path / "first.txt").write_text("alpha beta gamma\n")
    (tmp_path / "second.txt").write_text("alpha beta\n")

    tool = KeywordBM25Tool()
    params = KeywordParams(query="alpha", root=str(tmp_path), topk=1)

    result = tool.run(params)

    assert result.ok is True
    assert len(result.hits) == 1


def test_keyword_bm25_reports_missing_root(tmp_path: Path) -> None:
    """Missing roots are reported as errors with ``ok=False``."""
    missing_root = tmp_path / "missing"

    tool = KeywordBM25Tool()
    params = KeywordParams(query="anything", root=str(missing_root))

    result = tool.run(params)

    assert result.ok is False
    assert result.hits == []
    assert result.meta["error"] == "root-missing"


def test_keyword_bm25_ignores_symlinks_outside_root(tmp_path: Path) -> None:
    """Symlinked files that escape the root are not indexed."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "inside.txt").write_text("ranking algorithms inside\n")

    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_file = external_dir / "outside.txt"
    external_file.write_text("ranking data outside\n")

    link = repo_root / "link.txt"
    _create_symlink(link, external_file)

    tool = KeywordBM25Tool()
    params = KeywordParams(query="ranking", root=str(repo_root), topk=5)

    result = tool.run(params)

    assert result.ok is True
    paths = {hit.path for hit in result.hits}
    assert paths == {"inside.txt"}
