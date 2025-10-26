# User Manual / ユーザーマニュアル

## English

### Overview
The codeagent-lab project bundles reproducible experiments for source-code search. This manual covers local setup, command-line workflows, and operational tips for both keyless and semantic search domains.

### Prerequisites
- Python 3.13+ with [`uv`](https://github.com/astral-sh/uv) installed.
- External binaries on `PATH`:
  - [`rg`](https://github.com/BurntSushi/ripgrep) for the `grep` tool.
  - [`fd`](https://github.com/sharkdp/fd) for the `find` tool.
- Optional OpenAI access via `LAB_OPENAI_API_KEY` for semantic search.

### Environment Setup
1. Synchronize dependencies:
   ```bash
   uv sync
   ```
2. Copy the environment template and edit values as needed:
   ```bash
   cp .env.example .env
   ```
   - Leave `LAB_OPENAI_API_KEY` empty to run without semantic search.
   - Adjust storage paths (`LAB_DATA_ROOT`, etc.) if you prefer different directories.

### Running the CLI
Execute all commands with `uv run` to ensure they use the managed environment.

- Local tools that run without an API key:
  ```bash
  uv run lab tools run --domain grep --params-json '{"pattern":"TODO","root":"."}'
  uv run lab tools run --domain keyword --params-json '{"query":"vector store","root":"."}'
  uv run lab tools run --domain find --params-json '{"pattern":"*.py","root":"src"}'
  ```
- Semantic search (requires `LAB_OPENAI_API_KEY`):
  ```bash
  uv run lab tools run --domain semantic --params-json '{"query":"embedding factory","root":"."}'
  ```

### Additional Commands
- Inspect CLI entrypoints:
  ```bash
  uv run lab --help
  uv run lab tools openai-spec
  uv run lab-exp --help
  uv run lab-ui --help
  ```
- Launch the Streamlit dashboard (runs on the default port 8501):
  ```bash
  uv run lab-ui
  ```

### Troubleshooting
- Missing `rg`/`fd`: reinstall via your system package manager and confirm they appear in `which rg`/`which fd`.
- Authentication errors: verify `LAB_OPENAI_API_KEY` is present in `.env` and reload your shell.
- CLI JSON errors: ensure `--params-json` is valid JSON; wrap arguments in single quotes to avoid shell escaping issues.

---

## 日本語

### 概要
codeagent-lab プロジェクトは、ソースコード検索の再現可能な実験環境を提供します。本マニュアルでは、ローカルセットアップ、CLI ワークフロー、API キーの有無に応じた運用上の注意点を説明します。

### 前提条件
- Python 3.13 以上と [`uv`](https://github.com/astral-sh/uv) のインストール。
- `PATH` 上にある外部バイナリ:
  - `grep` ツール向けの [`rg`](https://github.com/BurntSushi/ripgrep)。
  - `find` ツール向けの [`fd`](https://github.com/sharkdp/fd)。
- セマンティック検索用に任意で設定する `LAB_OPENAI_API_KEY`。

### 環境セットアップ
1. 依存関係を同期します:
   ```bash
   uv sync
   ```
2. 環境変数テンプレートをコピーし、必要に応じて編集します:
   ```bash
   cp .env.example .env
   ```
   - セマンティック検索を使わない場合は `LAB_OPENAI_API_KEY` を空欄のままにできます。
   - `LAB_DATA_ROOT` などのパス設定は、好みに合わせて変更してください。

### CLI の実行
`uv run` を通じてコマンドを実行すると、管理された仮想環境が確実に使用されます。

- API キーが不要なローカルツール:
  ```bash
  uv run lab tools run --domain grep --params-json '{"pattern":"TODO","root":"."}'
  uv run lab tools run --domain keyword --params-json '{"query":"vector store","root":"."}'
  uv run lab tools run --domain find --params-json '{"pattern":"*.py","root":"src"}'
  ```
- セマンティック検索（`LAB_OPENAI_API_KEY` が必要）:
  ```bash
  uv run lab tools run --domain semantic --params-json '{"query":"embedding factory","root":"."}'
  ```

### 追加コマンド
- CLI エントリーポイントの確認:
  ```bash
  uv run lab --help
  uv run lab tools openai-spec
  uv run lab-exp --help
  uv run lab-ui --help
  ```
- Streamlit ダッシュボードの起動（デフォルトポートは 8501）:
  ```bash
  uv run lab-ui
  ```

### トラブルシューティング
- `rg` / `fd` が見つからない: パッケージマネージャーで再インストールし、`which rg` や `which fd` で確認してください。
- 認証エラー: `.env` に `LAB_OPENAI_API_KEY` が設定されているか確認し、シェルを再読み込みします。
- CLI の JSON エラー: `--params-json` の文字列が正しい JSON か確認し、シェルのエスケープ問題を避けるため単一引用符で囲んでください。
