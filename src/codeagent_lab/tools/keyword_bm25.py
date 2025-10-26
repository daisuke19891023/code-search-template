"""BM25 keyword search over repository files."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from rank_bm25 import BM25Okapi

from codeagent_lab.models import KeywordHit, KeywordParams, KeywordResult
from codeagent_lab.tools.protocols import Tool
from codeagent_lab.tools._path_filters import resolve_within_root


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


class _BM25Scorer(Protocol):
    """Subset of BM25 scorer functionality relied upon by the tool."""

    def get_scores(self, query: list[str]) -> list[float]:
        ...


@dataclass
class _Document:
    """Internal representation of a file considered for ranking."""

    path: Path
    tokens: list[str]


class KeywordBM25Tool(Tool[KeywordParams, KeywordResult]):
    """Rank repository files using BM25 scoring."""

    name = "keyword.bm25"
    Param = KeywordParams
    Result = KeywordResult

    max_file_bytes = 512_000

    def run(self, params: KeywordParams) -> KeywordResult:
        """Execute BM25 ranking over files under ``params.root``."""
        start = time.perf_counter()
        root = Path(params.root)
        if not root.is_dir():
            latency_ms = int((time.perf_counter() - start) * 1000)
            return KeywordResult(
                ok=False,
                hits=[],
                latency_ms=latency_ms,
                meta={"error": "root-missing", "root": str(root)},
            )

        documents = self._load_documents(root)
        query_tokens = self._tokenize(params.query)

        if not documents or not query_tokens:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return KeywordResult(
                hits=[],
                latency_ms=latency_ms,
                meta={"documents": len(documents), "query_tokens": len(query_tokens)},
            )

        bm25 = BM25Okapi([doc.tokens for doc in documents])
        scorer = cast("_BM25Scorer", bm25)
        raw_scores = scorer.get_scores(query_tokens)
        scores = [float(score) for score in raw_scores]

        topk = max(0, min(params.topk, len(scores)))
        ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)[:topk]

        hits = [
            KeywordHit(path=str(self._relative_path(root, documents[idx].path)), score=scores[idx])
            for idx in ranked_indices
        ]

        latency_ms = int((time.perf_counter() - start) * 1000)
        return KeywordResult(
            hits=hits,
            latency_ms=latency_ms,
            meta={"documents": len(documents), "query_tokens": len(query_tokens)},
        )

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Rank files using BM25 keyword scoring."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()

    def _load_documents(self, root: Path) -> list[_Document]:
        """Collect tokenized documents under ``root`` suitable for BM25."""
        documents: list[_Document] = []
        resolved_root = root.resolve()
        for path in sorted(root.rglob("*")):
            resolved = resolve_within_root(resolved_root, path)
            if resolved is None or not resolved.is_file():
                continue
            try:
                relative = resolved.relative_to(resolved_root)
            except ValueError:
                continue
            if any(part.startswith(".") for part in relative.parts if part not in {"", "."}):
                continue
            try:
                size = resolved.stat().st_size
            except OSError:
                continue
            if size > self.max_file_bytes:
                continue
            try:
                text = resolved.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "\x00" in text:
                continue
            tokens = self._tokenize(text)
            if not tokens:
                continue
            documents.append(_Document(path=resolved, tokens=tokens))

        return documents

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize ``text`` into lower-case alphanumeric tokens."""
        return [match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)]

    @staticmethod
    def _relative_path(root: Path, path: Path) -> Path:
        """Return ``path`` relative to ``root`` with graceful fallback."""
        try:
            return path.relative_to(root)
        except ValueError:
            resolved_root = root.resolve()
            try:
                return path.relative_to(resolved_root)
            except ValueError:
                return path
