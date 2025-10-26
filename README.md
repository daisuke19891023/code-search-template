# codeagent-lab

A template for building reproducible, comparable code-search experiments that expose the same tools to both internal Actions and LLM tool calls. The project provides a modular architecture (Factory + DI), structured experiment logging, Streamlit visualization, and Optuna-based optimization scaffolding.

## Quickstart
Follow these steps on a fresh machine to exercise every tool domain.

1. **Sync Python dependencies.** [`uv`](https://github.com/astral-sh/uv) manages the virtual environment and installs all Python requirements declared in `pyproject.toml`:
   ```bash
   uv sync
   ```
2. **Install external binaries.** The CLI shells out to the following executables; ensure they are on your `PATH`:
   - [`rg`](https://github.com/BurntSushi/ripgrep) for the `grep` tool.
   - [`fd`](https://github.com/sharkdp/fd) for the `find` tool.
3. **Configure environment variables.** Copy the template and populate values as needed:
   ```bash
   cp .env.example .env
   ```
   - `LAB_OPENAI_API_KEY` is **optional** but required for semantic search. Leave it empty to run the non-semantic tools only.
   - Other `LAB_*` settings already have sensible defaults for local experimentation; adjust paths if you prefer a different storage location.
4. **Run command-line tools.** All CLIs are exposed through `uv run` so they execute inside the managed environment.
   - Tools that rely on local binaries and do **not** need an API key:
     ```bash
     uv run lab tools run --domain grep --params-json '{"pattern":"TODO","root":"."}'
     uv run lab tools run --domain keyword --params-json '{"query":"vector store","root":"."}'
     uv run lab tools run --domain find --params-json '{"pattern":"*.py","root":"src"}'
     ```
   - Semantic search (requires `LAB_OPENAI_API_KEY` in your `.env`):
     ```bash
     uv run lab tools run --domain semantic --params-json '{"query":"embedding factory","root":"."}'
     ```
5. **Discover additional commands.** Inspect the CLI entrypoints and OpenAI tool specifications:
   ```bash
   uv run lab --help
   uv run lab tools openai-spec
   uv run lab-exp --help
   uv run lab-ui --help
   ```

Refer to `requirements.md`, `spec.md`, and `tasks.md` for detailed goals, architecture, and the full implementation backlog.

## クイックスタート（日本語）
新しい環境で各ツールドメインを試すための手順です。

1. **Python 依存関係を同期する。** [`uv`](https://github.com/astral-sh/uv) が仮想環境の作成と `pyproject.toml` に記載された Python 依存関係のインストールを行います:
   ```bash
   uv sync
   ```
2. **外部バイナリをインストールする。** CLI は以下の実行ファイルに依存しているため、`PATH` 上に配置してください:
   - `grep` ツールで使用する [`rg`](https://github.com/BurntSushi/ripgrep)。
   - `find` ツールで使用する [`fd`](https://github.com/sharkdp/fd)。
3. **環境変数を設定する。** テンプレートをコピーして必要な値を記入します:
   ```bash
   cp .env.example .env
   ```
   - `LAB_OPENAI_API_KEY` は **任意** ですが、セマンティック検索を使う場合には必須です。セマンティック以外のツールのみを試す場合は空のままで構いません。
   - その他の `LAB_*` 設定値はローカル検証向けの初期値が設定されています。必要であればストレージパスなどを調整してください。
4. **コマンドラインツールを実行する。** すべての CLI は `uv run` 経由で公開されており、管理された環境内で動作します。
   - ローカルバイナリに依存し、API キーが不要なツール:
     ```bash
     uv run lab tools run --domain grep --params-json '{"pattern":"TODO","root":"."}'
     uv run lab tools run --domain keyword --params-json '{"query":"vector store","root":"."}'
     uv run lab tools run --domain find --params-json '{"pattern":"*.py","root":"src"}'
     ```
   - セマンティック検索（`.env` に `LAB_OPENAI_API_KEY` が必要）:
     ```bash
     uv run lab tools run --domain semantic --params-json '{"query":"embedding factory","root":"."}'
     ```
5. **追加のコマンドを確認する。** CLI エントリーポイントと OpenAI ツール定義を確認できます:
   ```bash
   uv run lab --help
   uv run lab tools openai-spec
   uv run lab-exp --help
   uv run lab-ui --help
   ```

詳細な目標やアーキテクチャ、実装バックログについては `requirements.md`、`spec.md`、`tasks.md` を参照してください。
