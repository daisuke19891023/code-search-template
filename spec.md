# Specification

## 0. Goal & Scope
- Provide a template that enables natural-language to source code exploration tools to be consumed via internal Actions and LLM tool calls through a unified interface.
- Tool domains: `grep` (ripgrep), `keyword` (BM25), `semantic` (OpenAI embeddings + VectorStore), `ast` (tree-sitter, multi-language), `find` (fd).
- Architecture emphasizes Factory pattern + dependency injection for easy swapping and extension.
- Experiment management (logging, visualization) and optimization (Optuna) are bundled.
- External dependencies: `rg`, `fd`, tree-sitter language grammars, FAISS.

## 1. Technology Stack & Guidelines
- Python 3.11+
- Strict typing with Pyright (`pyrightconfig.json` included).
- Dependency management via `uv`.
- Settings provided through `pydantic-settings`.
- Structured logging with `structlog` (JSON output, context propagation).
- CLI built with Typer.
- LLM / Embeddings: OpenAI SDK.
- Vector store: FAISS (default) with extensible factory for Qdrant/Milvus/Chroma/PGVector, etc.
- AST analysis: tree-sitter with multi-language support.
- Experiment management: DuckDB + Parquet.
- Optimization: Optuna.
- UI: Streamlit with Graphviz for DAG rendering.

## 2. Architecture Overview
```
Settings ───▶ DI Container ─────┬──────────────────────────────┐
                                │                              │
                                ▼                              ▼
                         ToolFactory                 EmbeddingsFactory
                                │                              │
                                ▼                              ▼
                         Tool Protocol ───────────────▶ Semantic Tool
                                │                              │
                                ▼                              ▼
                         ActionAdapter              Core Services (Trace/Store/Tuner)
                                                             │
                                                             ▼
                                               Experiment Store (DuckDB+Parquet)
                                                             │
                                                             ▼
                                                      Streamlit UI
```
- Tool protocol: common `run(params) -> result` returning Pydantic models.
- Adapters expose tools for Actions and LLM tool calls using identical definitions.
- Factories instantiate tools, embeddings, vector stores, AST providers based on settings.
- Container injects logger, factories, store, and clients.
- Trace captures tool executions; experiments persist metrics and flow traces.

## 3. Data Models (Pydantic v2)
- `ToolParam`, `ToolResult` base classes with metadata and latency tracking.
- Domain-specific models:
  - Grep: `GrepParams`, `GrepHit`, `GrepResult` (pattern, root, extra args, hits).
  - Keyword (BM25): `KeywordParams`, `KeywordHit`, `KeywordResult`.
  - Semantic: `SemanticParams`, `SemanticHit`, `SemanticResult`.
  - AST: `AstParams`, `AstFinding`, `AstResult` (language list, optional scope globs, findings typed as `def`/`ref`/`call`/`note`).
  - Find: `FindParams`, `FindItem`, `FindResult`.
- Trace and experiments: `ToolCall` captures name, params, result summary, latency; `FlowTrace` collects calls, run id, metrics.

## 4. Settings (pydantic-settings)
- `Settings` class loads environment variables with prefix `LAB_` from `.env`.
- Configurable items: logging (level, JSON), backends (grep, keyword, semantic embedding provider, vector store, AST backend, languages), OpenAI credentials, storage locations (`data_root`, `duckdb_path`, `parquet_root`, `index_root`), UI host/port, Optuna storage/study.

## 5. Logging
- `logger.configure()` sets up structlog with contextvars, ISO timestamps, log levels, stack traces, and JSON or console rendering.
- Container provides logger; components acquire loggers via `structlog.get_logger(__name__)`.
- `contextvars` propagate `run_id` for consistent tracing.

## 6. Protocols & Factories
- Tool protocol defined via `Protocol` with generics for params/results; includes `describe()` and `json_schema()`.
- `ToolFactory` registers domain → tool instance mapping; supports retrieval and enumeration.
- Embeddings protocol ensures `embed(texts: List[str]) -> List[List[float]]`; OpenAI implementation uses `OpenAI` SDK.
- Vector store protocol covers `build`, `add`, `search`, `save`, `load`; FAISS implementation normalizes vectors, persists index + ids.
- `create_vector_index(backend, dim)` factory returns FAISS by default, raises on unknown backend.
- AST language provider protocol returns `Dict[str, Language]`; tree-sitter provider loads languages from supplied library paths; AST tool consumes provider + query definitions per language.

## 7. Tool Implementations (overview)
- **grep:** run `rg`, map hits to `GrepHit`, handle timeouts and exit codes.
- **keyword:** ingest file contents, compute BM25 scores, return top-k results.
- **semantic:** embed files via configured embeddings backend, manage vector index via factory (build/save/load), embed queries, perform search.
- **ast:** parse files for specified languages using tree-sitter, apply queries to extract findings.
- **find:** execute `fd` with optional type/pattern filters, return matched paths.

## 8. LLM Integration
- LLM factory builds OpenAI client using settings.
- Prompt store loads YAML templates via Jinja2.
- Tool adapter converts tool definitions to OpenAI function-calling schema and dispatches executions.

## 9. Dependency Injection Container / Bootstrap
- `Container` dataclass aggregates settings, logger, tool factory, embedding backend, vector DB, experiment store.
- `build_container()` loads settings, configures logger, registers tools (conditional semantic registration based on OpenAI credentials), sets up embeddings and vector store, instantiates experiment store.

## 10. Experiment Management & Optimization
- Experiment store writes run records to Parquet and DuckDB, enabling queries and UI display.
- Metrics include latency totals and relevance metrics (hits@k, precision@k, nDCG@k, etc.).
- Flow traces stored as JSON for DAG visualization.
- Optuna integration: `experiments/optimizer.py` defines objective functions; CLI triggers optimization with configured storage/study; default pruner `MedianPruner`, sampler `TPESampler`.

## 11. CLI Design (Typer)
- `codeagent_lab/cli/` hosts domain-specific CLIs:
  - `tools.py`: run individual tools, output OpenAI tool specs, dispatch LLM tool calls.
  - `experiments.py`: execute experiment pipelines and Optuna optimization.
  - `ui.py`: launch Streamlit UI.
  - `llm.py`: inspect OpenAI client/prompt configurations.
  - `vectordb.py`: build/search vector indexes.
  - `ast.py`: manage AST assets and indexes.
- Example commands:
  - `uv run lab tools run --domain grep --params-json '{"pattern":"TODO","root":"./"}'`
  - `uv run lab tools openai-spec`
  - `uv run lab-vdb build --root ./repo`
  - `uv run lab-exp run --pipeline find+grep+keyword --root ./repo --query "foo"`
  - `uv run lab-exp optimize --dataset ./datasets/cases.yaml --n-trials 40`
  - `uv run lab-ui start`

## 12. Directory Layout
```
codeagent-lab/
  pyproject.toml
  pyrightconfig.json
  README.md
  .env.example
  prompts/
    find_related.yaml
  ui/
    app.py
  codeagent_lab/
    __init__.py
    core.py
    container.py
    settings.py
    logger.py
    models.py
    tools/
      __init__.py
      protocols.py
      factory.py
      grep_ripgrep.py
      keyword_bm25.py
      semantic_openai.py
      ast_treesitter_multi.py
      find_fd.py
    embeddings/
      __init__.py
      protocols.py
      openai_embed.py
    vectordb/
      __init__.py
      protocols.py
      faiss_store.py
      factory.py
    ast/
      __init__.py
      protocols.py
      ts_provider.py
      queries/
        python.scm
        typescript.scm
        go.scm
    llm/
      __init__.py
      factory.py
      prompts.py
      tools_adapter.py
    experiments/
      __init__.py
      store.py
      optimizer.py
    cli/
      __init__.py
      tools.py
      experiments.py
      ui.py
      llm.py
      vectordb.py
      ast.py
  datasets/
    cases.yaml
```

## 13. Project Configuration (`pyproject.toml`)
- Metadata: name `codeagent-lab`, version `0.1.0`, Python `>=3.11`.
- Core dependencies: `pydantic`, `pydantic-settings`, `typer`, `structlog`, `orjson`, `rank-bm25`, `duckdb`, `pyarrow`, `pandas`, `jinja2`, `streamlit`, `openai`, `faiss-cpu`, `optuna`, `graphviz`.
- Optional dependencies:
  - `ast`: tree-sitter core + Python/JavaScript/Go grammars.
  - `dev`: pytest, pytest-cov, ruff, pyright.
- Console scripts: `lab`, `lab-ui`, `lab-exp`, `lab-vdb`.
- Tooling: Ruff configuration (line length 120, target py311), Pyright strict mode, Pytest markers.

## 14. Implementation Tasks (T1–T18)
1. **Project initialization:** scaffold structure, pyproject, pyright config, `.env.example`, ensure `uv run python -c "import codeagent_lab"` works and `uv run lab --help` executes.
2. **Settings & Logger:** implement `Settings` and structured logging; ensure boot log is emitted.
3. **Tool Protocol & Factory:** implement protocols and registry, ensure JSON schema generation works.
4. **grep (ripgrep):** implement command execution with timeout/error handling, returning `GrepResult`.
5. **keyword (BM25):** compute BM25 scores and return top-k results.
6. **Embeddings Factory (OpenAI):** implement protocols and embedder returning vectors with correct dimension.
7. **VectorStore (FAISS) + Factory:** support build/save/load/search with reproducibility.
8. **semantic Tool:** orchestrate embedding/indexing/search pipeline with persistence under `index_root`.
9. **AST multi-language:** implement provider and tool to extract definitions/references (start with Python support).
10. **find (fd):** execute `fd` with pattern/type filters.
11. **LLM Factory / PromptStore / ToolAdapter:** instantiate OpenAI client, render prompts, and emit OpenAI tool schemas.
12. **DI Container / core:** wire settings, logger, factories, vector store, embeddings, experiment store.
13. **Experiment Store:** persist runs to Parquet and DuckDB with incremental updates.
14. **CLI: tools / vectordb:** expose commands with meaningful error handling.
15. **UI (Streamlit):** show run list, metrics, DAG visualization, and result previews.
16. **Optuna integration:** implement optimizer and CLI command to run trials with pruner/sampler defaults.
17. **Lint/Type/Tests:** configure Ruff, Pyright, Pytest; ensure commands `uv run ruff check .`, `uv run pyright`, `uv run pytest -q` succeed with >=5 unit tests and >=1 E2E test.
18. **README / Quickstart:** document dependencies (`rg`, `fd`), environment variables, CLI usage, limitations; ensure instructions yield working setup.

## 15. UI Specification (Streamlit)
- Runs table from DuckDB showing `run_id`, timestamp, metrics.
- Run detail view: load trace JSON, list tool calls with latencies/summary, render DAG (Graphviz), preview top-k hits with snippet/score.

## 16. Security & Operations
- OpenAI API key supplied via environment only; never logged.
- External command invocation (`rg`, `fd`) must enforce timeouts and sanitize inputs.
- Consider encryption for Parquet/DuckDB storage when handling sensitive data.
- Tree-sitter language builds should be pinned/prebuilt for CI stability.

## 17. Future Extensions
- Additional vector stores (Qdrant, Milvus, Chroma, PGVector) following the common protocol.
- AST language expansion (Java, C#, Rust) plus advanced analyses (call graphs).
- LLM client additions (Claude, Vertex AI, Bedrock, etc.).
- Evaluation dataset management with labeled ground truth and automated scoring.
- Service exposure via FastAPI HTTP API with integrated UI.

## 18. Quickstart Summary
```
uv sync
# Install external tools: rg, fd

# Optional: configure OpenAI for semantic search
echo 'LAB_OPENAI_API_KEY=sk-...' >> .env

# Run grep
uv run lab tools run --domain grep --params-json '{"pattern":"TODO","root":"./"}'

# Build and query semantic index
uv run lab-vdb build --root ./your_repo
uv run lab-vdb search --query "rate limiting" --topk 10

# Log experiment and view UI
uv run lab-exp run --pipeline find+grep+keyword --root ./your_repo --query "auth middleware"
uv run lab-ui start
```
