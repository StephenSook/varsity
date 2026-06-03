from app.verification import verification_stage, verify


def test_all_critics_pass_when_grounded_and_consistent() -> None:
    p = verify(
        explanation="Under Law 11, the attacker was offside by 5.45 metres.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        proof_consistent=True,
    )
    assert p.verified is True
    assert len(p.critics) == 5
    assert all(c.passed for c in p.critics)


def test_fails_if_not_grounded() -> None:
    p = verify(
        explanation="Under Law 11, offside.",
        cites_law=True,
        grounded=False,
        screen_reader_ok=True,
    )
    assert p.verified is False
    assert not next(c for c in p.critics if c.name == "grounded").passed


def test_non_adjudication_critic_fails_when_proof_inconsistent() -> None:
    # the explanation disagrees with the rule proof -> the no-re-adjudication critic flags it
    p = verify(
        explanation="Under Law 11, offside.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        proof_consistent=False,
    )
    assert p.verified is False
    assert next(c for c in p.critics if c.name == "no-re-adjudication").passed is False


def test_substantive_critic_fails_on_empty() -> None:
    p = verify(explanation="off", cites_law=True, grounded=True, screen_reader_ok=True)
    assert next(c for c in p.critics if c.name == "substantive").passed is False


def test_verification_stage_shape() -> None:
    s = verification_stage(
        verify(
            explanation="Under Law 11, offside by 5 metres.",
            cites_law=True,
            grounded=True,
            screen_reader_ok=True,
        )
    )
    assert s["stage"] == "verification"
    assert s["total"] == 5
    assert s["passed"] == 5 and s["verified"] is True
    assert all({"name", "passed", "detail"} <= set(c) for c in s["critics"])
