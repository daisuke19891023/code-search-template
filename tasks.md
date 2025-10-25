# Implementation Tasks

## T1. Project Initialization
- Create the repository layout, `pyproject.toml`, `pyrightconfig.json`, `.env.example`, and package skeletons.
- Acceptance: `uv run python -c "import codeagent_lab"` succeeds. `uv run lab --help` displays CLI usage.

## T2. Settings & Logger
- Implement `Settings` (pydantic-settings) and structured logging via `structlog`.
- Acceptance: JSON structured boot log similar to `{ "event": "boot", "level": "info" }` appears when container initializes.

## T3. Tool Protocol & Factory
- Implement `tools/protocols.py` and `tools/factory.py`.
- Acceptance: `tool.Param.model_json_schema()` returns without error for each tool.

## T4. Grep (ripgrep)
- Build ripgrep wrapper that executes `rg`, parses hits, and handles non-zero exit codes/timeouts.
- Acceptance: `uv run lab tools run --domain grep --params-json '{"pattern":"TODO","root":"./"}'` returns structured hits.

## T5. Keyword (BM25)
- Implement BM25 ranking over repository files with configurable TopK.
- Acceptance: On a test corpus, the expected file ranks within the top results.

## T6. Embeddings Factory (OpenAI)
- Implement embedding protocol and OpenAI backend returning correct-dimension vectors.
- Acceptance: `embed(["hello"])` returns vectors with the model-specific length (e.g., 3072 for `text-embedding-3-large`).

## T7. VectorStore (FAISS) + Factory
- Implement FAISS index wrapper with build/save/load/search plus normalization.
- Acceptance: `build → save → load → search` yields consistent TopK results.

## T8. Semantic Tool
- Combine embeddings + vector index to perform semantic search with persisted indexes under `index_root`.
- Acceptance: On a small repo, conceptual queries surface expected files in Top-5.

## T9. AST Multi-language Support
- Implement tree-sitter provider and AST tool with language queries (initially Python).
- Acceptance: Fixture repository yields at least one definition/reference finding.

## T10. Find (fd)
- Implement fd wrapper respecting pattern/type filters.
- Acceptance: `--type file` returns files only in sample repo.

## T11. LLM Integration
- Implement OpenAI client factory, prompt rendering, and tool schema adapter.
- Acceptance: `uv run lab tools openai-spec` emits valid JSON function specifications.

## T12. DI Container / Core Assembly
- Wire settings, logger, tools, embeddings, vector store, and experiment store in `container.py`/`core.py`.
- Acceptance: Changing `vector_store_backend` selects the appropriate factory branch (future backends validated via tests).

## T13. Experiment Store
- Persist experiment runs to Parquet and DuckDB with incremental inserts.
- Acceptance: `SELECT COUNT(*) FROM runs` in DuckDB increases after logging new runs.

## T14. CLI: Tools & Vector DB
- Implement Typer commands for tool execution and vector DB operations with clear error messaging.
- Acceptance: Commands exit non-zero on error and print meaningful diagnostics.

## T15. Streamlit UI
- Build UI to list runs, show metrics, render DAGs, and preview TopK hits.
- Acceptance: UI loads recorded runs and displays tool call timeline with Graphviz DAG.

## T16. Optuna Integration
- Implement optimization objective wrapper and CLI entry (`lab-exp optimize`).
- Acceptance: Trial runs persist best value in Optuna study, demonstrating improvement over baseline.

## T17. Quality Gates
- Provide lint/type/test scaffolding (Ruff, Pyright, Pytest) with >=5 unit tests and >=1 E2E test.
- Acceptance: `uv run ruff check .`, `uv run pyright`, and `uv run pytest -q` all succeed.

## T18. Documentation
- Update README with quickstart, dependencies, CLI usage, and constraints; keep `.env.example` synchronized.
- Acceptance: Following README instructions reproduces baseline functionality (grep/keyword/find without API keys; semantic with key).
