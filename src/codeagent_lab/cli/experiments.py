"""CLI entry points for experiments and optimization."""

from __future__ import annotations

import typer

app = typer.Typer(help="Manage experiments and optimization workflows.")


@app.command()
def run(pipeline: str, root: str, query: str) -> None:
    """Run an experiment pipeline (not yet implemented)."""
    _ = pipeline, root, query
    typer.echo("Experiment execution is not implemented yet.", err=True)
    raise typer.Exit(code=1)


@app.command()
def optimize(dataset: str, n_trials: int = 10, timeout: int | None = None) -> None:
    """Run Optuna optimization (not yet implemented)."""
    _ = dataset, n_trials, timeout
    typer.echo("Optimization is not implemented yet.", err=True)
    raise typer.Exit(code=1)
