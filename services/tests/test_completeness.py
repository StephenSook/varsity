from app import completeness


def test_a_full_offside_narration_scores_complete() -> None:
    txt = (
        "When the ball was played, the most advanced attacker was 5.45 meters ahead of the "
        "second-to-last defender. That puts the player offside under Law 11."
    )
    r = completeness.score_offside(txt)
    assert r.complete is True
    assert r.score == 1.0
    assert r.dangling == []


def test_missing_margin_is_flagged_as_dangling() -> None:
    txt = "The attacker was offside under Law 11, ahead of the second-to-last defender."
    r = completeness.score_offside(txt)
    assert "margin" in r.dangling
    assert r.complete is False  # margin is the highest-weight disclosure for a blind fan


def test_within_noise_adds_a_tightness_disclosure() -> None:
    no_tight = "The attacker was offside under Law 11 by 0.02 m, past the second-to-last defender."
    r = completeness.score_offside(no_tight, within_noise=True)
    assert "tightness" in r.dangling  # a knife-edge call must disclose it is tight
    with_tight = no_tight + " This is a very tight, marginal call."
    r2 = completeness.score_offside(with_tight, within_noise=True)
    assert "tightness" not in r2.dangling and r2.complete is True


def test_is_disclosure_not_judgment() -> None:
    # the scorer only checks what the narration STATES; it never asserts the call was right/wrong
    r = completeness.score_offside("Offside by 5 m, Law 11, past the second-to-last defender.")
    joined = " ".join(d.detail for d in r.disclosures).lower()
    assert "states" in joined or "cites" in joined or "references" in joined
    assert "correct" not in joined and "should" not in joined


def test_stage_shape() -> None:
    s = completeness.completeness_stage(completeness.score_offside("Offside by 5 m under Law 11."))
    assert s["stage"] == "completeness"
    assert {"score", "complete", "disclosed", "total", "disclosures", "dangling"} <= set(s)
