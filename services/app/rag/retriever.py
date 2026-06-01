"""Retrieve the governing Law for a decision from the IFAB Law corpus.

Two retrieval paths share one interface:
- offline / CI: deterministic term-overlap keyword match (no network).
- online: re-rank with IBM Granite embeddings (cosine) when watsonx creds exist.

The curated ``laws.json`` (exact IFAB wording for Law 11 plus key laws) keeps the
demo self-contained; the full corpus is produced from the official PDF via
``app/rag/ingest.py`` (Docling) at build time.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

CORPUS = Path(__file__).resolve().parent / "laws.json"
GRANITE_EMBED_MODEL = "ibm/granite-embedding-278m-multilingual"
_WORD = re.compile(r"[a-z]+")


@dataclass
class LawChunk:
    law: str
    title: str
    text: str


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class LawRetriever:
    def __init__(self, corpus_path: Path | None = None) -> None:
        data = json.loads((corpus_path or CORPUS).read_text())
        self.chunks = [LawChunk(**c) for c in data]

    def _keyword(self, query: str) -> LawChunk:
        q = _tokens(query)

        def score(chunk: LawChunk) -> float:
            ct = _tokens(f"{chunk.title} {chunk.text}")
            return len(q & ct) / (math.sqrt(len(ct)) + 1)

        return max(self.chunks, key=score)

    def _embeddings(self, query: str) -> LawChunk:
        from app.llm import _watsonx

        texts = [query] + [f"{c.title}. {c.text}" for c in self.chunks]
        vectors = _watsonx.embed(GRANITE_EMBED_MODEL, texts)
        qv, doc_vecs = vectors[0], vectors[1:]
        best = max(range(len(self.chunks)), key=lambda i: _cosine(qv, doc_vecs[i]))
        return self.chunks[best]

    def retrieve(self, query: str, *, use_embeddings: bool = True) -> LawChunk:
        if use_embeddings and os.environ.get("WATSONX_API_KEY"):
            try:
                return self._embeddings(query)
            except Exception:
                pass
        return self._keyword(query)
