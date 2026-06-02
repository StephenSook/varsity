from app.rag.retriever import LawRetriever
from evals.run_eval import evaluate, load_golden


def test_rag_eval_meets_thresholds() -> None:
    """The committed RAG eval (offline BM25 path) must clear our published thresholds."""
    result = evaluate(LawRetriever(), load_golden(), use_embeddings=False)
    assert result.n >= 20
    assert result.hit_at_5 == 1.0  # every question finds its Law within the top 5
    assert result.hit_at_1 >= 0.85
    assert result.mrr >= 0.9


def test_offside_questions_route_to_law_11() -> None:
    """Every offside question routes to Law 11 at rank 1 (the demo-critical path)."""
    retriever = LawRetriever()
    offside = [g for g in load_golden() if g["law"] == "11"]
    assert len(offside) >= 6
    for g in offside:
        top = retriever.rank(g["q"], k=1, use_embeddings=False)[0]
        assert top.law == "11", f"{g['q']!r} -> Law {top.law}"
