from app.verification import ADVISORY, DETERMINISTIC, verification_stage, verify


def test_all_deterministic_pass_offside() -> None:
    p = verify(
        explanation="Under Law 11, the attacker was offside by 5.45 metres.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        proof_consistent=True,
        is_offside=True,
    )
    assert p.verified is True
    assert len(p.of_kind(DETERMINISTIC)) == 5  # +verdict-consistent on the offside path
    assert len(p.of_kind(ADVISORY)) == 2
    assert all(c.passed for c in p.critics)


def test_guardian_false_positive_does_not_flip_the_hard_gate() -> None:
    p = verify(
        explanation="Under Law 11, the attacker was offside by 5.45 metres.",
        cites_law=True,
        grounded=False,  # Guardian flake
        screen_reader_ok=True,
        is_offside=True,
    )
    assert p.verified is True
    grounded = next(c for c in p.critics if c.name == "grounded")
    assert grounded.kind == ADVISORY and grounded.passed is False


def test_neutral_critic_flags_editorializing() -> None:
    p = verify(
        explanation="Under Law 11, the attacker was offside, but the referee was wrong here.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        is_offside=True,
    )
    assert p.verified is False
    critic = next(c for c in p.critics if c.name == "neutral")
    assert critic.kind == DETERMINISTIC and critic.passed is False


def test_verdict_consistent_catches_a_flipped_verdict() -> None:
    # is_offside=True but the narration says "onside" -> the round-trip re-parse flags it.
    p = verify(
        explanation="Under Law 11, the attacker was onside by 5.45 metres.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        is_offside=True,
    )
    assert p.verified is False
    critic = next(c for c in p.critics if c.name == "verdict-consistent")
    assert critic.kind == DETERMINISTIC and critic.passed is False


def test_verdict_consistent_absent_without_is_offside() -> None:
    p = verify(
        explanation="Under Law 14, a penalty was awarded.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
    )
    assert not any(c.name == "verdict-consistent" for c in p.critics)
    assert p.verified is True


def test_non_adjudication_critic_flips_the_gate() -> None:
    p = verify(
        explanation="Under Law 11, offside.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        proof_consistent=False,
        is_offside=True,
    )
    assert p.verified is False
    assert next(c for c in p.critics if c.name == "no-re-adjudication").passed is False


def test_verification_stage_shape() -> None:
    s = verification_stage(
        verify(
            explanation="Under Law 14, a penalty was awarded.",
            cites_law=True,
            grounded=False,
            screen_reader_ok=True,
        )
    )
    assert s["stage"] == "verification"
    assert s["verified"] is True  # all deterministic pass
    assert s["hard_passed"] == 4 and s["hard_total"] == 4  # no verdict-consistent (no is_offside)
    assert s["advisory_passed"] == 1 and s["advisory_total"] == 2  # grounded flagged
    assert all({"name", "passed", "detail", "kind"} <= set(c) for c in s["critics"])
