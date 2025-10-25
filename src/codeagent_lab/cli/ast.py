"""CLI entry points for AST utilities."""

from __future__ import annotations

import typer

app = typer.Typer(help="Manage tree-sitter assets and AST utilities.")


@app.command()
def languages() -> None:
    """List configured AST languages (not yet implemented)."""
    typer.echo("AST language management is not implemented yet.", err=True)
    raise typer.Exit(code=1)
