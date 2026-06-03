from fastapi.testclient import TestClient

from app import decisions
from app.llm.granite import _fallback_decision
from app.llm.guardian import GuardianVerdict, cites_law_clause
from app.main import app
from app.pipeline import decision_stages
from app.rag.retriever import LawRetriever


class FakeGranite:
    def explain_decision(self, *, incident, outcome, law, law_text, language="English"):
        return f"Under Law {law}, the decision was {outcome}, grounded in the Law text."


class FakeGuardian:
    def check(self, explanation, *, law_context=""):
        c = cites_law_clause(explanation)
        return GuardianVerdict(safe=c, cites_law=c, grounded=True, model_answer="No")


def _stages(name: str) -> dict:
    return {
        s["stage"]: s
        for s in decision_stages(name, granite=FakeGranite(), guardian=FakeGuardian())
    }


def test_retriever_maps_decisions_to_their_governing_law() -> None:
    """The real RAG returns Law 14 for the penalty query and Law 12 for handball."""
    r = LawRetriever()
    assert r.retrieve(decisions.DECISIONS["penalty"]["law_query"]).law == "14"
    assert r.retrieve(decisions.DECISIONS["handball"]["law_query"]).law == "12"


def test_decision_stages_order_and_content() -> None:
    stages = list(decision_stages("penalty", granite=FakeGranite(), guardian=FakeGuardian()))
    assert [s["stage"] for s in stages] == [
        "trigger",
        "decision",
        "signal",
        "law",
        "granite",
        "guardian",
        "verification",
        "provenance",
        "verdict",
    ]
    by = {s["stage"]: s for s in stages}
    assert by["trigger"]["tier"] == "illustrative"
    assert by["decision"]["decision_type"] == "penalty"
    assert by["law"]["law"] == "14"
    assert by["verdict"]["decision_type"] == "penalty"
    assert by["verdict"]["safe"] is True
    assert "Law 14" in by["verdict"]["text"]


def test_handball_maps_to_law_12() -> None:
    assert _stages("handball")["law"]["law"] == "12"


def test_unknown_decision_falls_back_to_default() -> None:
    assert _stages("bogus")["decision"]["decision_type"] == decisions.DEFAULT_DECISION


def test_decision_fallback_cites_law_in_each_language() -> None:
    for lang in ("English", "Spanish", "French", "Portuguese", "German"):
        txt = _fallback_decision(law="14", outcome="Penalty kick awarded", language=lang)
        assert cites_law_clause(txt), (lang, txt)


def test_decisions_endpoint_lists_penalty_and_handball() -> None:
    idx = TestClient(app).get("/decisions").json()["decisions"]
    assert {d["decision_type"] for d in idx} == {"penalty", "handball"}
    assert all(d["tier"] == "illustrative" for d in idx)
