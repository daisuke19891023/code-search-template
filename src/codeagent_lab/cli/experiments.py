"""CLI entry points for experiments and optimization."""

from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from codeagent_lab.experiments.optimizer import run_optimization
from codeagent_lab.settings import Settings

app = typer.Typer(help="Manage experiments and optimization workflows.")


@app.command()
def run(pipeline: str, root: str, query: str) -> None:
    """Run an experiment pipeline (not yet implemented)."""
    _ = pipeline, root, query
    typer.echo("Experiment execution is not implemented yet.", err=True)
    raise typer.Exit(code=1)


@app.command()
def optimize(dataset: str, n_trials: int = 10, timeout: int | None = None) -> None:
    """Execute Optuna optimization on the provided evaluation dataset."""
    dataset_path = Path(dataset)
    if not dataset_path.exists():
        typer.secho(f"Dataset not found: {dataset_path}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)
    if n_trials <= 0:
        typer.secho("n-trials must be greater than zero", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        settings = Settings()
    except (ValidationError, ValueError) as exc:
        typer.secho(f"Failed to load settings: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    dataset_config, study = run_optimization(
        dataset_path=dataset_path,
        storage=str(settings.optuna_storage),
        study_name=settings.optuna_study,
        n_trials=n_trials,
        timeout=timeout,
    )

    if not study.trials:
        typer.secho("No trials were completed.", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    best_value = study.best_value
    if best_value <= dataset_config.baseline_score:
        typer.secho(
            "Optimization did not beat the baseline."
            f" best={best_value:.4f} baseline={dataset_config.baseline_score:.4f}",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    typer.echo(
        "Optimization complete."
        f" Best value: {best_value:.4f} (baseline {dataset_config.baseline_score:.4f})."
        f" Best trial: {study.best_trial.number}.",
    )
