"""Dependency injection container for codeagent-lab."""

from __future__ import annotations

from dataclasses import dataclass

from codeagent_lab.ast.ts_provider import TreeSitterProvider
from codeagent_lab.embeddings.openai_embed import OpenAIEmbedding
from codeagent_lab.experiments.store import ExperimentStore
from codeagent_lab.logger import configure
from codeagent_lab.settings import Settings
from codeagent_lab.tools import ast_treesitter_multi, find_fd, grep_ripgrep, keyword_bm25, semantic_openai
from codeagent_lab.tools.factory import ToolFactory
from codeagent_lab.vectordb.factory import create_vector_index


@dataclass
class Container:
    """Aggregates configured application services."""

    settings: Settings
    logger: object
    tools: ToolFactory
    embeddings: object | None
    vectordb: object | None
    store: ExperimentStore


def build_container() -> Container:
    """Build the dependency container using default settings."""
    settings = Settings()
    logger = configure(settings.log_level, settings.log_json)
    tools = ToolFactory()

    embedder: OpenAIEmbedding | None = None
    vectordb = None
    if settings.openai_api_key:
        embedder = OpenAIEmbedding(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_embedding_model,
        )
        vectordb = create_vector_index(settings.vector_store_backend, dim=3072)

    tools.register("grep", grep_ripgrep.RipgrepTool())
    tools.register("keyword", keyword_bm25.KeywordBM25Tool())
    tools.register("find", find_fd.FdTool())

    if embedder and vectordb:
        tools.register("semantic", semantic_openai.SemanticOpenAITool(embedder, vectordb, str(settings.index_root)))

    provider = TreeSitterProvider({})
    tools.register("ast", ast_treesitter_multi.TreeSitterTool(provider=provider, queries={}))

    store = ExperimentStore(settings.duckdb_path, settings.parquet_root)
    logger.info("boot")
    return Container(
        settings=settings,
        logger=logger,
        tools=tools,
        embeddings=embedder,
        vectordb=vectordb,
        store=store,
    )
