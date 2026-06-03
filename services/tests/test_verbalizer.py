"""Tests for the Coqatoo-style deterministic proof-tree verbalizer."""

from __future__ import annotations

from app.law11 import prove
from app.verbalizer import verbalize, verbalize_stage


def _offside_proof():
    return prove(
        is_offside=True,
        margin_meters=0.3,
        beyond_defender=True,
        beyond_ball=True,
        attacker_x=100.0,
    )


def _onside_proof():
    return prove(
        is_offside=False,
        margin_meters=-0.3,
        beyond_defender=False,
        beyond_ball=True,
        attacker_x=100.0,
    )


def test_offside_verbalization_is_faithful_to_the_proof():
    text = verbalize(_offside_proof())
    assert "offside under Law 11" in text
    assert "opponents' half" in text
    assert "second-to-last opponent" in text
    assert "onside" not in text


def test_onside_verbalization_states_the_failing_condition():
    text = verbalize(_onside_proof())
    assert "onside under Law 11" in text
    assert "level with or behind the second-to-last opponent" in text


def test_verbalizer_is_total_and_deterministic():
    proof = _offside_proof()
    a, b = verbalize(proof), verbalize(proof)
    assert a == b
    assert len(a) > 40  # never empty


def test_stage_verdict_matches_the_proof():
    assert verbalize_stage(_offside_proof())["verdict"] == "offside"
    assert verbalize_stage(_onside_proof())["verdict"] == "onside"
    assert verbalize_stage(_offside_proof())["faithful_by_construction"] is True
