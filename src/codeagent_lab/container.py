"""Dependency injection container for codeagent-lab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from codeagent_lab.ast.ts_provider import TreeSitterProvider
from codeagent_lab.embeddings.openai_embed import OpenAIEmbedding
from codeagent_lab.experiments.store import ExperimentStore
from codeagent_lab.logger import configure
from codeagent_lab.settings import Settings
from codeagent_lab.tools import ast_treesitter_multi, find_fd, grep_ripgrep, keyword_bm25, semantic_openai
from codeagent_lab.tools.factory import ToolFactory
from codeagent_lab.vectordb.factory import create_vector_index

if TYPE_CHECKING:  # pragma: no cover - typing only
    from structlog.stdlib import BoundLogger
    from codeagent_lab.embeddings.protocols import EmbeddingBackend
    from codeagent_lab.vectordb.protocols import VectorIndex
else:  # pragma: no cover - runtime placeholder
    BoundLogger = object
    EmbeddingBackend = object
    VectorIndex = object


@dataclass
class Container:
    """Aggregates configured application services."""

    settings: Settings
    logger: BoundLogger
    tools: ToolFactory
    embeddings: EmbeddingBackend | None
    vectordb: VectorIndex | None
    store: ExperimentStore


def build_container(settings: Settings | None = None) -> Container:
    """Build the dependency container using default settings."""
    resolved_settings = settings or Settings()
    logger = cast("BoundLogger", configure(resolved_settings.log_level, resolved_settings.log_json))
    tools = ToolFactory()

    _register_core_tools(tools, resolved_settings)

    embedder = _create_embedding_backend(resolved_settings)
    vectordb = _create_vector_index(resolved_settings, embedder)
    if embedder is not None and vectordb is not None:
        tools.register(
            "semantic",
            semantic_openai.SemanticOpenAITool(
                embedder=embedder,
                index=vectordb,
                index_root=str(resolved_settings.index_root),
            ),
        )

    if resolved_settings.ast_backend != "tree_sitter":
        message = f"unsupported AST backend: {resolved_settings.ast_backend}"
        raise ValueError(message)
    provider = TreeSitterProvider({})
    tools.register(
        "ast",
        ast_treesitter_multi.TreeSitterTool(provider=provider, queries={}),
    )

    store = ExperimentStore(resolved_settings.duckdb_path, resolved_settings.parquet_root)
    logger.info(
        "boot",
        embed_backend=resolved_settings.semantic_embed_backend,
        vector_store=resolved_settings.vector_store_backend,
    )
    return Container(
        settings=resolved_settings,
        logger=logger,
        tools=tools,
        embeddings=embedder,
        vectordb=vectordb,
        store=store,
    )


def _register_core_tools(tools: ToolFactory, settings: Settings) -> None:
    """Register the always-available tools based on configuration."""
    if settings.grep_backend != "ripgrep":
        message = f"unsupported grep backend: {settings.grep_backend}"
        raise ValueError(message)
    tools.register("grep", grep_ripgrep.RipgrepTool())

    if settings.keyword_backend != "bm25":
        message = f"unsupported keyword backend: {settings.keyword_backend}"
        raise ValueError(message)
    tools.register("keyword", keyword_bm25.KeywordBM25Tool())

    find_backend = getattr(settings, "find_backend", "fd")
    if find_backend != "fd":
        message = f"unsupported find backend: {find_backend}"
        raise ValueError(message)
    tools.register("find", find_fd.FdTool())


def _create_embedding_backend(settings: Settings) -> EmbeddingBackend | None:
    """Instantiate the embedding backend according to configuration."""
    backend = settings.semantic_embed_backend
    if backend in {"none", "disabled"}:
        return None
    if backend == "openai":
        if not settings.openai_api_key:
            return None
        return OpenAIEmbedding(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_embedding_model,
        )
    message = f"unsupported semantic embedding backend: {backend}"
    raise ValueError(message)


def _create_vector_index(
    settings: Settings,
    embedder: EmbeddingBackend | None,
) -> VectorIndex | None:
    """Create the configured vector index when embeddings are available."""
    if embedder is None:
        return None
    return create_vector_index(settings.vector_store_backend, dim=embedder.dimension)
