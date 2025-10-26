"""Streamlit application for browsing experiment runs."""

from __future__ import annotations

import importlib
import json
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from graphviz import Digraph
import streamlit as st

from codeagent_lab.models import FlowTrace, ToolCall
from codeagent_lab.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

StrDict = dict[str, Any]
try:
    _pyarrow_lib = importlib.import_module("pyarrow.lib")
    _pyarrow_invalid = _pyarrow_lib.ArrowInvalid
except Exception:  # pragma: no cover - defensive import guard
    _pyarrow_invalid = Exception

try:
    _pyarrow_parquet = importlib.import_module("pyarrow.parquet")
    _pyarrow_read_table = _pyarrow_parquet.read_table
except Exception:  # pragma: no cover - fallback when pyarrow missing
    def _pyarrow_read_table(_path: str | pathlib.Path) -> Any:
        message = "pyarrow is required to read experiment runs"
        raise RuntimeError(message)


if isinstance(_pyarrow_invalid, type) and issubclass(_pyarrow_invalid, Exception):
    ArrowInvalid = _pyarrow_invalid
else:  # pragma: no cover - defensive fallback
    ArrowInvalid = Exception


def read_table(path: str | pathlib.Path) -> Any:
    """Proxy to ``pyarrow.parquet.read_table`` with graceful fallback."""
    return _pyarrow_read_table(path)



@dataclass(frozen=True)
class RunRecord:
    """Single experiment run loaded from persisted Parquet data."""

    run_id: str
    params: dict[str, Any]
    metrics: dict[str, float]
    trace: FlowTrace
    path: pathlib.Path


def _load_json(value: Any) -> dict[str, Any]:
    """Load JSON-encoded payloads from Parquet values."""
    result: dict[str, Any] = {}
    if isinstance(value, str) and value:
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return result
        if isinstance(data, dict):
            return cast("StrDict", data)
        return result
    if isinstance(value, dict):
        return cast("StrDict", value)
    return result


def load_run_records(parquet_root: pathlib.Path) -> list[RunRecord]:
    """Return all experiment runs stored under ``parquet_root``."""
    if not parquet_root.exists():
        return []

    records: list[RunRecord] = []
    for path in sorted(parquet_root.glob("*.parquet")):
        try:
            table = read_table(path)
        except (OSError, ArrowInvalid):
            continue
        for row in table.to_pylist():
            if not isinstance(row, dict):
                continue
            row_dict = cast("StrDict", row)
            record = _record_from_row(row_dict, path)
            if record is not None:
                records.append(record)

    records.sort(key=lambda record: record.path.stat().st_mtime, reverse=True)
    return records


def _record_from_row(row: dict[str, Any], path: pathlib.Path) -> RunRecord | None:
    """Convert a Parquet row dictionary into a ``RunRecord`` if possible."""
    run_id_raw = row.get("run_id")
    if run_id_raw is None:
        return None
    run_id = str(run_id_raw)
    if not run_id:
        return None

    params = _load_json(row.get("params"))
    metrics = _parse_metrics(_load_json(row.get("metrics")))
    trace_payload = _load_json(row.get("trace"))
    try:
        trace = FlowTrace.model_validate(trace_payload)
    except ValueError:
        return None
    return RunRecord(
        run_id=run_id,
        params=params,
        metrics=metrics,
        trace=trace,
        path=path,
    )


def _parse_metrics(metrics_raw: dict[str, Any]) -> dict[str, float]:
    """Convert metric values to floats where possible."""
    parsed: dict[str, float] = {}
    for key, value in metrics_raw.items():
        try:
            parsed[key] = float(value)
        except (TypeError, ValueError):
            continue
    return parsed


@st.cache_data(show_spinner=False)
def _cached_run_records(parquet_root: str) -> list[RunRecord]:
    """Cache run records loaded from disk."""
    return load_run_records(pathlib.Path(parquet_root))


def build_flow_graph(trace: FlowTrace) -> Digraph:
    """Create a Graphviz DAG for the provided tool call trace."""
    graph_obj = Digraph(
        "flow",
        graph_attr={"rankdir": "LR", "splines": "spline"},
        node_attr={"shape": "box", "style": "rounded,filled", "fillcolor": "#EEF3FF"},
    )

    graph: Any = graph_obj

    if not trace.calls:
        graph.node("no_calls", "No tool calls recorded")
        return graph_obj

    previous_node: str | None = None
    for index, call in enumerate(trace.calls, start=1):
        node_id = f"step_{index}"
        summary = _summarise_result(call)
        label_lines = [f"{index}. {call.name}", f"{call.latency_ms} ms"]
        if summary:
            label_lines.append(summary)
        graph.node(node_id, "\n".join(label_lines))
        if previous_node is not None:
            graph.edge(previous_node, node_id)
        previous_node = node_id
    return graph_obj


def _summarise_result(call: ToolCall) -> str:
    """Return a compact textual summary for a tool call result."""
    items: list[str] = []
    for key, value in call.result_summary.items():
        if isinstance(value, (int, float, str)):
            items.append(f"{key}={value}")
    return ", ".join(items[:3])


def _format_params(params: dict[str, Any]) -> str:
    """Pretty-print run parameters for tabular display."""
    if not params:
        return "-"
    return json.dumps(params, ensure_ascii=False, indent=2)


def _display_dataframe(rows: Sequence[Mapping[str, object]]) -> None:
    """Render tabular data via Streamlit while keeping typing explicit."""
    st.write(list(rows))


def render() -> None:
    """Render the experiment browser UI."""
    st.set_page_config(page_title="codeagent-lab", layout="wide")
    st.title("codeagent-lab Runs")

    settings = Settings()

    runs = _cached_run_records(str(settings.parquet_root))

    if not runs:
        st.info("No experiment runs were found under the configured Parquet directory.")
        st.caption(f"Parquet directory: {settings.parquet_root}")
        return

    run_options = {record.run_id: record for record in runs}
    sidebar = st.sidebar
    sidebar.header("Runs")
    selected_run_id = sidebar.selectbox("Select a run", options=list(run_options), index=0)
    selected_run = run_options[selected_run_id]

    sidebar.subheader("Metrics")
    if selected_run.metrics:
        for name, value in selected_run.metrics.items():
            sidebar.metric(label=name, value=value)
    else:
        sidebar.caption("No metrics recorded.")

    st.subheader("Run Overview")
    overview_rows: list[dict[str, object]] = [
        {
            "Run ID": record.run_id,
            "Calls": len(record.trace.calls),
            "Metrics": ", ".join(f"{k}={v}" for k, v in record.metrics.items()) or "-",
        }
        for record in runs
    ]
    _display_dataframe(overview_rows)

    st.subheader("Parameters")
    st.code(_format_params(selected_run.params), language="json")

    st.subheader("Tool Calls")
    if selected_run.trace.calls:
        call_rows: list[dict[str, object]] = []
        for index, call in enumerate(selected_run.trace.calls, start=1):
            call_rows.append(
                {
                    "Step": index,
                    "Tool": call.name,
                    "Latency (ms)": call.latency_ms,
                    "Result Summary": json.dumps(call.result_summary, ensure_ascii=False),
                },
            )
        _display_dataframe(call_rows)
    else:
        st.info("No tool calls were recorded for this run.")

    st.subheader("Flow DAG")
    graph = build_flow_graph(selected_run.trace)
    st.graphviz_chart(graph)
