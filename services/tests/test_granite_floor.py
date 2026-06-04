from app.llm.granite import _fallback_decision, _fallback_explanation
from app.llm.guardian import cites_law_clause
from app.verification import TOO_CLOSE_HEDGE


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


def test_too_close_floor_hedges_cites_the_law_and_quotes_no_number() -> None:
    # A within-noise call must NOT quote a precise margin (false precision); it hedges and defers.
    txt = _fallback_explanation(
        margin_meters=0.02, is_offside=True, language="English", within_noise=True
    )
    assert cites_law_clause(txt)
    assert TOO_CLOSE_HEDGE.search(txt)  # acknowledges the data limit
    assert "offside" in txt
    # no precise metre/centimetre margin: only Law 11 and the honest noise figure may appear
    from app.uncertainty import SIGMA_MARGIN_M

    noise_cm = str(round(SIGMA_MARGIN_M * 100))
    digits = txt.replace("11", "").replace(noise_cm, "")
    assert not any(ch.isdigit() for ch in digits)


def test_decision_floor_still_cites_the_law() -> None:
    txt = _fallback_decision(law="14", outcome="Penalty awarded", language="English")
    assert cites_law_clause(txt)
