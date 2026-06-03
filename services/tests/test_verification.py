from app.verification import ADVISORY, DETERMINISTIC, verification_stage, verify


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


def test_guardian_groundedness_false_positive_does_not_flip_the_hard_gate() -> None:
    # The tuning: Guardian is advisory. A model "not grounded" flag is reported but does NOT
    # flip the deterministic hard gate when the deterministic checks all pass.
    p = verify(
        explanation="Under Law 11, the attacker was offside by 5.45 metres.",
        cites_law=True,
        grounded=False,  # Guardian flake
        screen_reader_ok=True,
        proof_consistent=True,
    )
    assert p.verified is True  # hard gate unaffected
    grounded = next(c for c in p.critics if c.name == "grounded")
    assert grounded.kind == ADVISORY and grounded.passed is False


def test_non_adjudication_critic_is_deterministic_and_flips_the_gate() -> None:
    # The coded security property stays dispositive: a proof conflict flips verified.
    p = verify(
        explanation="Under Law 11, offside.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        proof_consistent=False,
    )
    assert p.verified is False
    critic = next(c for c in p.critics if c.name == "no-re-adjudication")
    assert critic.kind == DETERMINISTIC and critic.passed is False


def test_substantive_critic_fails_on_empty() -> None:
    p = verify(explanation="off", cites_law=True, grounded=True, screen_reader_ok=True)
    assert p.verified is False
    assert next(c for c in p.critics if c.name == "substantive").passed is False


def test_verification_stage_shape() -> None:
    s = verification_stage(
        verify(
            explanation="Under Law 11, offside by 5 metres.",
            cites_law=True,
            grounded=False,
            screen_reader_ok=True,
        )
    )
    assert s["stage"] == "verification"
    assert s["total"] == 5
    assert s["verified"] is True  # all 3 deterministic pass
    assert s["hard_passed"] == 3 and s["hard_total"] == 3
    assert s["advisory_passed"] == 1 and s["advisory_total"] == 2  # grounded flagged
    assert all({"name", "passed", "detail", "kind"} <= set(c) for c in s["critics"])
