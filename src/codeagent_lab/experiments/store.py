"""Persistence layer for experiment runs."""

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING, Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from codeagent_lab.models import FlowTrace


class ExperimentStore:
    """Persist experiment metrics and traces."""

    def __init__(self, duckdb_path: pathlib.Path, parquet_root: pathlib.Path) -> None:
        """Initialise the store with storage locations."""
        self._duckdb_path = pathlib.Path(duckdb_path)
        self._duckdb_path.parent.mkdir(parents=True, exist_ok=True)
        self._parquet_root = pathlib.Path(parquet_root)
        self._parquet_root.mkdir(parents=True, exist_ok=True)

    def log_run(
        self,
        run_id: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        trace: FlowTrace,
    ) -> None:
        """Persist a single run to Parquet and DuckDB."""
        record = {
            "run_id": run_id,
            "params": json.dumps(params, ensure_ascii=False),
            "metrics": json.dumps(metrics, ensure_ascii=False),
            "trace": json.dumps(trace.model_dump(mode="json"), ensure_ascii=False),
        }
        table = pa.Table.from_pylist([record])
        pq_path = self._parquet_root / f"{run_id}.parquet"
        pq.write_table(table, str(pq_path))
        with duckdb.connect(self._duckdb_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT,
                    params JSON,
                    metrics JSON,
                    trace JSON
                )
                """,
            )
            conn.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?)",
                [record["run_id"], record["params"], record["metrics"], record["trace"]],
            )
