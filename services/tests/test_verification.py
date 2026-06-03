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
    # cites-law, no-re-adjudication, neutral, substantive, verdict-consistent, calibration
    assert len(p.of_kind(DETERMINISTIC)) == 6
    assert len(p.of_kind(ADVISORY)) == 2
    assert all(c.passed for c in p.critics)


def _calib(explanation: str, within_noise: bool):
    p = verify(
        explanation=explanation,
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        is_offside=True,
        within_noise=within_noise,
    )
    return next(c for c in p.critics if c.name == "calibration")


def test_calibration_passes_a_clear_call_with_a_confident_number() -> None:
    assert _calib("Under Law 11, the attacker was clearly offside by 5.69 metres.", False).passed


def test_calibration_requires_a_hedge_on_a_too_close_call() -> None:
    # A too-close call that quotes a confident precise number with no hedge fails calibration.
    assert not _calib("Under Law 11, the attacker was offside by 0.02 metres.", True).passed
    # The same call, hedged as too close to resolve, passes.
    assert _calib(
        "Under Law 11, this was too close for our freeze-frame data to resolve - an Umpire's "
        "Call - so VARSITY describes the official decision: offside.",
        True,
    ).passed


def test_calibration_rejects_overconfidence_on_a_too_close_call() -> None:
    assert not _calib(
        "Under Law 11, the attacker was clearly offside, within the measurement noise.", True
    ).passed


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


def test_grounded_in_law_passes_when_rule_phrases_are_in_the_law() -> None:
    p = verify(
        explanation="The attacker was in an offside position, nearer the goal line than the "
        "second-to-last opponent.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        is_offside=True,
        law_text="A player is in an offside position if nearer to the goal line than the "
        "second-to-last opponent. Offside position is judged at the moment the ball is played.",
    )
    critic = next(c for c in p.critics if c.name == "grounded-in-law")
    assert critic.kind == DETERMINISTIC and critic.passed is True


def test_grounded_in_law_flags_a_rule_phrase_absent_from_the_retrieved_law() -> None:
    # the narration asserts "gaining an advantage" but the retrieved Law text lacks it
    p = verify(
        explanation="The attacker was offside, gaining an advantage from the rebound.",
        cites_law=True,
        grounded=True,
        screen_reader_ok=True,
        is_offside=True,
        law_text="A player is in an offside position if nearer the goal line than the ball.",
    )
    assert p.verified is False
    assert next(c for c in p.critics if c.name == "grounded-in-law").passed is False


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
