"""Retrieve the governing Law for a decision from the IFAB Law corpus.

The corpus (``index/chunks.json``) and the FAISS index (``index/laws.faiss``) are
produced once at build time by ``app/rag/ingest.py``: Docling converts the official
IFAB Laws of the Game 2025/26 PDF to structured text, it is split into one chunk per
Law, and each chunk is embedded with IBM Granite embeddings.

Two retrieval paths share one interface:
- online: embed the query with the SAME Granite model and search the FAISS index
  (exact inner-product over L2-normalised vectors, i.e. cosine).
- offline / CI: deterministic term-overlap keyword match over the same corpus, no
  network and no FAISS/numpy import.

The Granite query model must match the model the index was built with; ingest and
retriever share ``GRANITE_EMBED_MODEL`` so they cannot drift apart.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.rag import corpus_signature

INDEX_DIR = Path(__file__).resolve().parent / "index"
CORPUS = INDEX_DIR / "chunks.json"
SIGNATURE = INDEX_DIR / "chunks.sig.json"
FAISS_INDEX = INDEX_DIR / "laws.faiss"
GRANITE_EMBED_MODEL = "ibm/granite-embedding-278m-multilingual"
_WORD = re.compile(r"[a-z]+")
# Stop-words stripped from Law titles so "the"/"of" do not earn a title-match bonus.
_STOP = {"the", "of", "and", "a", "an", "in", "on", "to"}


@dataclass
class LawChunk:
    law: str
    title: str
    text: str


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


class LawRetriever:
    def __init__(self, corpus_path: Path | None = None, *, verify_integrity: bool = True) -> None:
        path = corpus_path or CORPUS
        data = json.loads(path.read_text())
        # LLM08 RAG-poisoning defense: verify the canonical corpus against its signed
        # SHA-256 manifest and FAIL CLOSED on a mismatch (a tampered Law would otherwise
        # silently corrupt an explanation a blind user cannot visually fact-check). The
        # canonical corpus MUST be signed - a missing manifest fails closed too, so an
        # attacker cannot bypass the check by deleting the signature (easier than forging
        # it). Custom corpora (test fixtures) are a different path and skip verification.
        self.corpus_root: str | None = None
        if verify_integrity and path.resolve() == CORPUS.resolve():
            manifest = corpus_signature.load_manifest(SIGNATURE)
            if manifest is None:
                raise corpus_signature.CorpusIntegrityError("the canonical Law corpus is unsigned")
            self.corpus_root = corpus_signature.verify_or_raise(data, manifest)
        self.chunks = [LawChunk(law=c["law"], title=c["title"], text=c["text"]) for c in data]
        self._index = None  # lazy-loaded FAISS index (online path only)
        self._build_bm25()

    def _build_bm25(self) -> None:
        """Precompute BM25 stats for the offline/CI keyword path.

        The title is weighted (counted twice) since "Penalty Kick" in the title is a
        far stronger signal than the same words buried in another Law's body. IDF
        downweights tokens common across Laws (goal, kick, ball) and rewards the
        distinctive ones (offside, penalty), which a plain overlap score does not.
        """
        self._docs = [_tokens(f"{c.title} {c.text}") for c in self.chunks]
        self._title_tokens = [set(_tokens(c.title)) - _STOP for c in self.chunks]
        self._tf = [Counter(d) for d in self._docs]
        self._len = [len(d) for d in self._docs]
        self._avgdl = (sum(self._len) / len(self._len)) if self._len else 1.0
        n = len(self.chunks)
        df: Counter[str] = Counter()
        for doc in self._docs:
            df.update(set(doc))
        self._idf = {t: math.log((n - c + 0.5) / (c + 0.5) + 1) for t, c in df.items()}

    # A query token that matches the canonical Law title ("The Penalty Kick") is
    # decisive: it outranks a body that merely mentions the words a lot (Law 10's
    # penalty shoot-out is penalty-heavy but is not "the penalty kick").
    _TITLE_BONUS = 4.0

    def _keyword_scores(self, query: str, k1: float = 1.5, b: float = 0.75) -> list[float]:
        q = _tokens(query)
        qset = set(q)
        scores: list[float] = []
        for i in range(len(self.chunks)):
            tf, dl = self._tf[i], self._len[i]
            total = 0.0
            for t in q:
                idf = self._idf.get(t)
                f = tf.get(t, 0)
                if not idf or not f:
                    continue
                total += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / self._avgdl))
            for t in qset & self._title_tokens[i]:
                total += self._TITLE_BONUS * max(self._idf.get(t, 0.0), 1.0)
            scores.append(total)
        return scores

    def _keyword(self, query: str) -> LawChunk:
        scores = self._keyword_scores(query)
        return self.chunks[max(range(len(self.chunks)), key=scores.__getitem__)]

    def _faiss(self):
        if self._index is None:
            import faiss  # runtime dep (faiss-cpu), imported only on the online path

            self._index = faiss.read_index(str(FAISS_INDEX))
        return self._index

    def _embed_query(self, query: str):
        import faiss
        import numpy as np

        from app.llm import _watsonx

        qv = np.asarray(_watsonx.embed(GRANITE_EMBED_MODEL, [query]), dtype="float32")
        faiss.normalize_L2(qv)
        return qv

    def _embeddings(self, query: str) -> LawChunk:
        _, ids = self._faiss().search(self._embed_query(query), 1)
        return self.chunks[int(ids[0][0])]

    def _online(self, use_embeddings: bool) -> bool:
        return use_embeddings and bool(os.environ.get("WATSONX_API_KEY")) and FAISS_INDEX.exists()

    def retrieve(self, query: str, *, use_embeddings: bool = True) -> LawChunk:
        if self._online(use_embeddings):
            try:
                return self._embeddings(query)
            except Exception:
                pass
        return self._keyword(query)

    def rank(self, query: str, *, k: int = 5, use_embeddings: bool = True) -> list[LawChunk]:
        """Return the top-k chunks in descending relevance (for hit@k / MRR evaluation)."""
        k = min(k, len(self.chunks))
        if self._online(use_embeddings):
            try:
                _, ids = self._faiss().search(self._embed_query(query), k)
                return [self.chunks[int(i)] for i in ids[0] if i >= 0]
            except Exception:
                pass
        scores = self._keyword_scores(query)
        order = sorted(range(len(self.chunks)), key=scores.__getitem__, reverse=True)
        return [self.chunks[i] for i in order[:k]]
