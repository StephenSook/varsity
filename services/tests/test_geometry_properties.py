"""Property-based tests for the offside geometry (the 5.45/5.69 m anchor is a smoke test, not a
correctness test - these catch the sign, translation, and scaling bugs an anchor cannot)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.geometry import METERS_PER_UNIT, FreezeFramePlayer, compute_offside

# Positions in the opponents' half, away from the exact halfway line, leaving headroom to shift.
_x = st.floats(min_value=62.0, max_value=118.0, allow_nan=False, allow_infinity=False)


def _frame(attacker_x, def_a, def_b, keeper_x):
    return [
        FreezeFramePlayer(x=attacker_x, y=40.0, teammate=True),
        FreezeFramePlayer(x=30.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=def_a, y=40.0, teammate=False),
        FreezeFramePlayer(x=def_b, y=41.0, teammate=False),
        FreezeFramePlayer(x=keeper_x, y=40.0, teammate=False, keeper=True),
    ]


@given(attacker_x=_x, def_a=_x, def_b=_x, keeper_x=_x, delta=st.floats(-1.0, 1.0))
def test_translation_invariance_along_x(attacker_x, def_a, def_b, keeper_x, delta):
    """Shifting every x by the same amount leaves the (no-ball) margin unchanged."""
    base = compute_offside(_frame(attacker_x, def_a, def_b, keeper_x))
    shifted = compute_offside(
        _frame(attacker_x + delta, def_a + delta, def_b + delta, keeper_x + delta)
    )
    assert shifted.margin_meters == pytest.approx(base.margin_meters, abs=0.01)


@given(attacker_x=_x, def_a=_x, def_b=_x, keeper_x=_x, s=st.floats(0.6, 1.4))
def test_scaling_homogeneity(attacker_x, def_a, def_b, keeper_x, s):
    """Scaling every x by s scales the margin by s (the margin is a linear x-distance)."""
    base = compute_offside(_frame(attacker_x, def_a, def_b, keeper_x))
    scaled = compute_offside(_frame(attacker_x * s, def_a * s, def_b * s, keeper_x * s))
    assert scaled.margin_meters == pytest.approx(s * base.margin_meters, abs=0.05)


@given(attacker_x=_x, def_a=_x, def_b=_x, keeper_x=_x)
def test_sign_consistency_with_the_defender_line(attacker_x, def_a, def_b, keeper_x):
    """With no ball, the margin's sign agrees with being beyond the second-to-last opponent."""
    r = compute_offside(_frame(attacker_x, def_a, def_b, keeper_x))
    if r.margin_meters > 0.05:
        assert r.beyond_defender is True
    if r.margin_meters < -0.05:
        assert r.beyond_defender is False


@given(attacker_x=_x, def_a=_x, def_b=_x, keeper_x=_x)
def test_margin_uses_the_yard_conversion(attacker_x, def_a, def_b, keeper_x):
    """The reported margin is the x-unit gap times the international yard, not Euclidean."""
    r = compute_offside(_frame(attacker_x, def_a, def_b, keeper_x))
    expected = round((r.attacker_x - r.reference_x) * METERS_PER_UNIT, 2)
    assert r.margin_meters == pytest.approx(expected, abs=0.001)
