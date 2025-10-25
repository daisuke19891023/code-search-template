"""CLI entry points for tool execution."""

from __future__ import annotations

import json

import typer

app = typer.Typer(help="Run code search tools and inspect their schemas.")


@app.command()
def run(domain: str, params_json: str) -> None:
    """Run a tool with JSON parameters (not yet implemented)."""
    _ = domain, params_json
    typer.echo("Tool execution is not implemented yet.", err=True)
    raise typer.Exit(code=1)


@app.command("openai-spec")
def openai_spec(domain: str | None = None) -> None:
    """Print the OpenAI function schema for the registered tools."""
    _ = domain
    typer.echo(json.dumps({"error": "tool schema not wired"}, indent=2))
