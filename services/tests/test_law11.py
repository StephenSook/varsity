from app.law11 import proof_payload, prove


def test_clear_offside_proof_is_consistent_and_concludes_offside() -> None:
    p = prove(
        is_offside=True, margin_meters=5.45, beyond_defender=True, beyond_ball=True, attacker_x=72.2
    )
    assert p.derived_offside is True
    assert p.consistent_with_decision is True
    assert "Offside under Law 11" in p.conclusion
    keys = {s.key for s in p.steps}
    assert {
        "position.half",
        "position.beyond_defender",
        "position.beyond_ball",
        "offence.active_involvement",
    } <= keys
    defeaters = [s for s in p.steps if s.role == "defeater"]
    assert len(defeaters) == 3 and all(s.status == "n/a" for s in defeaters)


def test_onside_proof_concludes_onside() -> None:
    p = prove(
        is_offside=False,
        margin_meters=-3.01,
        beyond_defender=False,
        beyond_ball=True,
        attacker_x=50.0,
    )
    assert p.derived_offside is False
    assert p.consistent_with_decision is True
    assert "Onside under Law 11" in p.conclusion
    assert not any(s.key == "offence.active_involvement" for s in p.steps)


def test_tight_call_notes_measurement_noise() -> None:
    p = prove(
        is_offside=True,
        margin_meters=0.02,
        beyond_defender=True,
        beyond_ball=True,
        attacker_x=72.0,
        within_noise=True,
    )
    bd = next(s for s in p.steps if s.key == "position.beyond_defender")
    assert "measurement noise" in bd.claim
    assert "borderline level call" in bd.claim


def test_never_adjudicates_when_engine_disagrees_with_official() -> None:
    # geometry derives onside, but the official decided offside -> VARSITY trusts the official
    p = prove(
        is_offside=True,
        margin_meters=-0.10,
        beyond_defender=False,
        beyond_ball=True,
        attacker_x=70.0,
    )
    assert p.derived_offside is False
    assert p.consistent_with_decision is False
    assert "VARSITY trusts the official" in p.conclusion
    assert "decision stands" in p.conclusion


def test_proof_payload_shape() -> None:
    p = prove(
        is_offside=True, margin_meters=5.45, beyond_defender=True, beyond_ball=True, attacker_x=72.2
    )
    payload = proof_payload(p)
    assert payload["stage"] == "proof"
    assert payload["consistent"] is True
    assert all(
        {"key", "claim", "status", "law", "role", "clause"} <= set(s) for s in payload["steps"]
    )


def test_steps_carry_finer_clause_descriptors() -> None:
    # finer than the bare Law number: each step names its specific Law-11 condition
    p = prove(
        is_offside=True, margin_meters=5.45, beyond_defender=True, beyond_ball=True, attacker_x=72.2
    )
    by_key = {s.key: s.clause for s in p.steps}
    assert by_key["position.beyond_defender"] == "beyond the second-to-last opponent"
    assert by_key["position.beyond_ball"] == "beyond the ball"
    assert by_key["defeater.goal_kick"] == "goal-kick exception"
