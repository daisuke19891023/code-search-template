"""CLI entry point for launching the Streamlit UI."""

from __future__ import annotations

import typer

app = typer.Typer(help="Launch the codeagent-lab UI.")


@app.command("start")
def start_ui(host: str = "localhost", port: int = 8501) -> None:
    """Start the Streamlit UI (not yet implemented)."""
    _ = host, port
    typer.echo("UI launch is not implemented yet.", err=True)
    raise typer.Exit(code=1)
