from app.llm.granite import _fallback_decision, _fallback_explanation
from app.llm.guardian import cites_law_clause


def test_en_offside_floor_is_given_new_and_cites_the_law() -> None:
    # given-before-new order: lead with where the players were, verdict + Law last
    txt = _fallback_explanation(margin_meters=5.45, is_offside=True, language="English")
    assert txt.startswith("When the ball was played")
    assert "offside under Law 11" in txt
    assert cites_law_clause(txt) and "onside" not in txt


def test_en_onside_floor_is_given_new_and_cites_the_law() -> None:
    txt = _fallback_explanation(margin_meters=-3.01, is_offside=False, language="English")
    assert txt.startswith("When the ball was played")
    assert "onside under Law 11" in txt
    assert cites_law_clause(txt)


def test_decision_floor_still_cites_the_law() -> None:
    txt = _fallback_decision(law="14", outcome="Penalty awarded", language="English")
    assert cites_law_clause(txt)
