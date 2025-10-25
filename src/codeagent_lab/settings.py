"""Application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration object for the laboratory runtime."""

    model_config = SettingsConfigDict(env_prefix="LAB_", env_file=".env", extra="allow")

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    # Backends (Factory keys)
    grep_backend: str = "ripgrep"
    keyword_backend: str = "bm25"
    semantic_embed_backend: str = "openai"
    vector_store_backend: str = "faiss"
    ast_backend: str = "tree_sitter"
    ast_languages: list[str] = ["python"]

    # OpenAI
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"

    # Storage
    data_root: Path = Path(".labdata")
    duckdb_path: Path = Path(".labdata/experiments.duckdb")
    parquet_root: Path = Path(".labdata/parquet")
    index_root: Path = Path(".labdata/indexes")

    # UI
    ui_host: str = "localhost"
    ui_port: int = 8501

    optuna_storage: str = "sqlite:///./.labdata/optuna.db"
    optuna_study: str = "codeagent_lab_default"
