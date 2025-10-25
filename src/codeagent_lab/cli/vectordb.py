"""CLI entry points for vector index management."""

from __future__ import annotations

import typer

app = typer.Typer(help="Manage vector indexes for semantic search.")


@app.command()
def build(root: str) -> None:
    """Build a vector index (not yet implemented)."""
    _ = root
    typer.echo("Vector index build is not implemented yet.", err=True)
    raise typer.Exit(code=1)


@app.command()
def search(query: str, topk: int = 10) -> None:
    """Search a vector index (not yet implemented)."""
    _ = query, topk
    typer.echo("Vector index search is not implemented yet.", err=True)
    raise typer.Exit(code=1)
