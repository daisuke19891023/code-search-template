"""Tests for the tree-sitter AST tool."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

import pytest

from codeagent_lab.ast.ts_provider import TreeSitterProvider
from codeagent_lab.models import AstParams
from codeagent_lab.tools.ast_treesitter_multi import TreeSitterTool

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType


pytest.importorskip("tree_sitter")
pytest.importorskip("tree_sitter_python")


def _create_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip the test when unsupported."""
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks not supported: {exc}")


def _write_sample_project(root: Path) -> None:
    """Write a minimal Python module with two functions and calls."""
    module = root / "package" / "module.py"
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text(
        """
def foo(value: int) -> int:
    return value + 1


def bar() -> int:
    return foo(41)


result = foo(1)
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_extracts_python_definitions_and_references(tmp_path: Path) -> None:
    """The AST tool returns both definitions and references for Python code."""
    _write_sample_project(tmp_path)

    provider = TreeSitterProvider()
    tool = TreeSitterTool(provider=provider, queries=None)
    params = AstParams(root=str(tmp_path), languages=["python"], symbol=None)

    result = tool.run(params)

    definitions = [finding for finding in result.findings if finding.kind == "def"]
    references = [finding for finding in result.findings if finding.kind == "ref"]

    assert any(finding.text == "foo" for finding in definitions)
    assert any(finding.text == "foo" for finding in references)
    assert result.ok is True
    assert result.meta["executor"] == "tree-sitter"


def test_symbol_filter_limits_findings(tmp_path: Path) -> None:
    """Applying a symbol filter restricts the findings to that identifier."""
    _write_sample_project(tmp_path)

    provider = TreeSitterProvider()
    tool = TreeSitterTool(provider=provider, queries=None)
    params = AstParams(root=str(tmp_path), languages=["python"], symbol="bar")

    result = tool.run(params)

    assert all(finding.text == "bar" for finding in result.findings)
    assert any(finding.kind == "def" for finding in result.findings)


def test_tree_sitter_ignores_symlinks_outside_root(tmp_path: Path) -> None:
    """Symlinked files outside the repository are ignored."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_sample_project(repo_root)

    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_file = external_dir / "outside.py"
    external_file.write_text("""def baz() -> None:\n    pass\n""", encoding="utf-8")

    _create_symlink(repo_root / "link.py", external_file)

    provider = TreeSitterProvider()
    tool = TreeSitterTool(provider=provider, queries=None)
    params = AstParams(root=str(repo_root), languages=["python"], symbol=None)

    result = tool.run(params)

    assert result.ok is True
    assert all(finding.text != "baz" for finding in result.findings)


def test_language_missing_when_module_import_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Import failures are treated as missing languages rather than raising."""
    provider = TreeSitterProvider()
    original_import = import_module

    def failing_import(name: str, package: str | None = None) -> ModuleType:
        if name == "tree_sitter_python":
            raise ImportError("boom")
        return original_import(name, package)

    monkeypatch.setattr("codeagent_lab.ast.ts_provider.import_module", failing_import)

    languages = provider.get_languages(["python"])

    assert "python" not in languages
