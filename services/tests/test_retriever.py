from app.rag.retriever import LawRetriever


def test_offside_query_retrieves_law_11() -> None:
    r = LawRetriever()
    # force the offline keyword path (no network in CI)
    chunk = r.retrieve("offside attacker ahead of the second-last defender", use_embeddings=False)
    assert chunk.law == "11"
    assert "offside" in chunk.text.lower()


def test_penalty_query_retrieves_law_14() -> None:
    r = LawRetriever()
    chunk = r.retrieve("penalty kick goalkeeper on the goal line", use_embeddings=False)
    assert chunk.law == "14"
