"""CLI entry points for vector index management."""

from __future__ import annotations

from typing import Any

import typer
from pydantic import ValidationError

from codeagent_lab.container import build_container
from codeagent_lab.models import SemanticParams

app = typer.Typer(help="Manage vector indexes for semantic search.")


def _get_semantic_tool() -> Any:
    """Return the registered semantic tool or exit with an error."""
    container = build_container()
    try:
        tool = container.tools.get("semantic")
    except KeyError as exc:
        message = (
            "Semantic tool is not configured. "
            "Set LAB_OPENAI_API_KEY and enable embeddings to use vector commands."
        )
        typer.echo(message, err=True)
        raise typer.Exit(code=1) from exc
    return tool


@app.command()
def build(
    root: str = typer.Option(..., "--root", "-r", help="Repository root to index."),
) -> None:
    """Build or refresh the semantic vector index for ``root``."""
    tool = _get_semantic_tool()
    try:
        params = SemanticParams(query="", root=root, topk=0)
    except ValidationError as exc:
        typer.echo(exc.json(), err=True)
        raise typer.Exit(code=1) from exc

    try:
        result = tool.run(params)
    except Exception as exc:  # pragma: no cover - defensive safety net
        typer.echo(f"Failed to build index: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not result.ok:
        error_message = result.meta.get("error", "semantic tool reported failure")
        typer.echo(f"Failed to build index: {error_message}", err=True)
        raise typer.Exit(code=1)

    index_meta = result.meta.get("index", {})
    status = "built" if index_meta.get("built") else "reused"
    path = index_meta.get("path", "<unknown>")
    documents = result.meta.get("documents", 0)
    typer.echo(f"Index {status} at {path} ({documents} documents indexed)")


@app.command()
def search(
    query: str = typer.Option(..., "--query", "-q", help="Search query text."),
    root: str = typer.Option(".", "--root", "-r", help="Repository root to search."),
    topk: int = typer.Option(10, "--topk", "-k", help="Number of results to return."),
) -> None:
    """Execute a semantic vector search against a built index."""
    tool = _get_semantic_tool()
    try:
        params = SemanticParams(query=query, root=root, topk=topk)
    except ValidationError as exc:
        typer.echo(exc.json(), err=True)
        raise typer.Exit(code=1) from exc

    try:
        result = tool.run(params)
    except Exception as exc:  # pragma: no cover - defensive safety net
        typer.echo(f"Search failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not result.ok:
        error_message = result.meta.get("error", "semantic tool reported failure")
        typer.echo(f"Search failed: {error_message}", err=True)
        raise typer.Exit(code=1)

    typer.echo(result.model_dump_json(indent=2))
