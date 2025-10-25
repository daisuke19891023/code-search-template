"""CLI helpers for LLM diagnostics."""

from __future__ import annotations

import typer

app = typer.Typer(help="Inspect LLM configuration and prompts.")


@app.command()
def info() -> None:
    """Print information about the configured LLM (not yet implemented)."""
    typer.echo("LLM diagnostics are not implemented yet.", err=True)
    raise typer.Exit(code=1)
