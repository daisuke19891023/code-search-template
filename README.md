# codeagent-lab

A template for building reproducible, comparable code-search experiments that expose the same tools to both internal Actions and LLM tool calls. The project provides a modular architecture (Factory + DI), structured experiment logging, Streamlit visualization, and Optuna-based optimization scaffolding.

## Quickstart
1. Install dependencies with [`uv`](https://github.com/astral-sh/uv):
   ```bash
   uv sync
   ```
2. Install external binaries:
   - [`rg`](https://github.com/BurntSushi/ripgrep) (ripgrep)
   - [`fd`](https://github.com/sharkdp/fd)
3. (Optional) Configure OpenAI credentials for semantic search:
   ```bash
   cp .env.example .env
   # populate LAB_OPENAI_API_KEY and related settings
   ```
4. Explore the CLI placeholders:
   ```bash
   uv run lab --help
   uv run lab tools openai-spec
   ```

Refer to `requirements.md`, `spec.md`, and `tasks.md` for detailed goals, architecture, and the full implementation backlog.
