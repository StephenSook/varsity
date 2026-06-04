"""Tests for the match-discourse state (references RECEIVED decisions, never predicts)."""

from app import discourse


def test_first_decision_has_no_connective() -> None:
    s = discourse.MatchState()
    assert discourse.connective(s, key="a", is_offside=True, band="clear") == ""


def test_a_second_tight_call_is_counted_and_named() -> None:
    s = discourse.MatchState()
    discourse.record(s, key="a", is_offside=True, band="tight")
    c = discourse.connective(s, key="b", is_offside=True, band="very tight")
    assert "second tight call so far" in c
    assert "the same outcome as the previous review" in c


def test_opposite_verdict_is_contrasted() -> None:
    s = discourse.MatchState()
    discourse.record(s, key="a", is_offside=True, band="clear")
    c = discourse.connective(s, key="b", is_offside=False, band="clear")
    assert "in contrast to the previous offside review" in c


def test_a_review_of_the_same_moment_adds_nothing_and_does_not_inflate() -> None:
    s = discourse.MatchState()
    discourse.record(s, key="a", is_offside=True, band="tight")
    # re-viewing the same moment: empty connective, and record is a no-op
    assert discourse.connective(s, key="a", is_offside=True, band="tight") == ""
    discourse.record(s, key="a", is_offside=True, band="tight")
    assert len(s.history) == 1
    assert s.tight_count == 1


def test_moment_key_is_stable_per_verdict_and_margin() -> None:
    assert discourse.moment_key(True, 5.691) == discourse.moment_key(True, 5.694)
    assert discourse.moment_key(True, 5.69) != discourse.moment_key(False, 5.69)


def test_store_is_per_match_and_resettable() -> None:
    discourse.reset_match("m1")
    a = discourse.for_match("m1")
    discourse.record(a, key="x", is_offside=True, band="clear")
    assert len(discourse.for_match("m1").history) == 1
    discourse.reset_match("m1")
    assert len(discourse.for_match("m1").history) == 0
