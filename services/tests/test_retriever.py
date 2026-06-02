import json

from app.rag.retriever import CORPUS, FAISS_INDEX, LawRetriever


def test_offside_query_retrieves_law_11() -> None:
    r = LawRetriever()
    # force the offline BM25 keyword path (no network in CI)
    chunk = r.retrieve("offside attacker ahead of the second-last defender", use_embeddings=False)
    assert chunk.law == "11"
    assert "offside" in chunk.text.lower()


def test_penalty_query_retrieves_law_14() -> None:
    r = LawRetriever()
    chunk = r.retrieve("penalty kick goalkeeper on the goal line", use_embeddings=False)
    assert chunk.law == "14"


def test_corpus_is_the_real_docling_ingest() -> None:
    """The corpus is the Docling-ingested IFAB Laws, not a hand-curated stub."""
    r = LawRetriever()
    laws = {c.law for c in r.chunks}
    # all 17 Laws of the Game plus the VAR protocol chunk
    assert {str(n) for n in range(1, 18)} <= laws
    assert "VAR" in laws
    # Law 11 carries the real IFAB wording, not a paraphrase
    law11 = next(c for c in r.chunks if c.law == "11")
    assert "second-last opponent" in law11.text
    assert len(law11.text) > 1500  # the full multi-section Law, for the Detail panel


def test_faiss_index_matches_corpus() -> None:
    """The committed FAISS index has one vector per corpus chunk (built at ingest)."""
    import faiss

    n_chunks = len(json.loads(CORPUS.read_text()))
    index = faiss.read_index(str(FAISS_INDEX))
    assert index.ntotal == n_chunks
    assert index.d == 768  # Granite embedding dimension
