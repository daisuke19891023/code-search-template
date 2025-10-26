"""CLI entry points for tool execution."""

from __future__ import annotations

import json

from typing import Any

from pydantic import ValidationError

from codeagent_lab.container import build_container

import typer

app = typer.Typer(help="Run code search tools and inspect their schemas.")


@app.command()
def run(domain: str, params_json: str) -> None:
    """Run a tool with JSON parameters."""
    try:
        payload: dict[str, Any] = json.loads(params_json)
    except json.JSONDecodeError as exc:  # pragma: no cover - exercised in CLI usage
        typer.echo(f"Invalid JSON: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    container = build_container()
    try:
        tool = container.tools.get(domain)
    except KeyError as exc:  # pragma: no cover - validated via CLI tests
        typer.echo(f"Unknown tool domain: {domain}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        params = tool.Param.model_validate(payload)
    except ValidationError as exc:
        typer.echo(exc.json(), err=True)
        raise typer.Exit(code=1) from exc

    result = tool.run(params)
    typer.echo(result.model_dump_json(indent=2))


@app.command("openai-spec")
def openai_spec(domain: str | None = None) -> None:
    """Print the OpenAI function schema for the registered tools."""
    container = build_container()
    domains = (
        [(domain, container.tools.get(domain))]
        if domain is not None
        else container.tools.items()
    )

    spec = {
        name: {
            "name": tool.name,
            "description": tool.describe(),
            "parameters": tool.Param.model_json_schema(),
        }
        for name, tool in domains
    }
    typer.echo(json.dumps(spec, indent=2))
