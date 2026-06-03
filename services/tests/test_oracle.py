from app.llm.granite import _fallback_answer, _first_sentence
from app.llm.guardian import GuardianVerdict, cites_law_clause
from app.pipeline import question_stages
from app.rag.retriever import LawRetriever


class FakeGranite:
    def answer_question(self, *, question, law, title, law_text, language="English"):
        return f"Under Law {law} ({title}), here is the grounded answer to: {question}."


class FakeGuardian:
    def check(self, explanation, *, law_context=""):
        c = cites_law_clause(explanation)
        return GuardianVerdict(safe=c, cites_law=c, grounded=True, model_answer="No")


def test_oracle_retrieves_a_relevant_law() -> None:
    r = LawRetriever()
    assert r.retrieve("why was the goal disallowed for offside").law == "11"
    assert r.retrieve("what is a corner kick").law == "17"


def test_question_stages_order_and_grounding() -> None:
    stages = list(
        question_stages("why was the goal offside", granite=FakeGranite(), guardian=FakeGuardian())
    )
    assert [s["stage"] for s in stages] == [
        "trigger",
        "law",
        "granite",
        "guardian",
        "verification",
        "provenance",
        "verdict",
    ]
    by = {s["stage"]: s for s in stages}
    assert by["trigger"]["question"] == "why was the goal offside"
    assert by["law"]["law"] == "11"
    assert by["verdict"]["question"] == "why was the goal offside"
    assert by["verdict"]["safe"] is True
    assert "Law 11" in by["verdict"]["text"]


def test_oracle_fallback_quotes_and_cites_the_law() -> None:
    law_text = (
        "## Law 17\n\n## The Corner Kick\n\nA corner kick is awarded when the ball wholly "
        "passes over the goal line. More text."
    )
    for lang in ("English", "Spanish", "French", "Portuguese", "German"):
        ans = _fallback_answer(law="17", title="The Corner Kick", law_text=law_text, language=lang)
        assert cites_law_clause(ans), (lang, ans)
        assert "corner kick is awarded" in ans.lower()


def test_first_sentence_skips_markdown_headers() -> None:
    text = "## Law 11\n\n## Offside\n\nIt is not an offence to be in an offside position. More."
    assert _first_sentence(text) == "It is not an offence to be in an offside position."
