"""Property-based (Hypothesis) + metamorphic verification of the offside engine.

Metamorphic relations need no oracle: they assert that a transformation of the input which
should NOT change the verdict indeed leaves it unchanged. These three lines expose nearly every
coordinate-frame bug (per the neuro-symbolic verification report).
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app import law11
from app.geometry import HALFWAY_X, FreezeFramePlayer, compute_offside

_x = st.floats(min_value=1.0, max_value=119.0, allow_nan=False, allow_infinity=False)
_y = st.floats(min_value=1.0, max_value=79.0, allow_nan=False, allow_infinity=False)


@st.composite
def frames(draw) -> list[FreezeFramePlayer]:
    """A valid freeze-frame: one candidate attacker, the passer, two defenders + a keeper."""
    return [
        FreezeFramePlayer(x=draw(_x), y=draw(_y), teammate=True),
        FreezeFramePlayer(x=draw(_x), y=draw(_y), teammate=True, actor=True),
        FreezeFramePlayer(x=draw(_x), y=draw(_y), teammate=False),
        FreezeFramePlayer(x=draw(_x), y=draw(_y), teammate=False),
        FreezeFramePlayer(x=draw(_x), y=draw(_y), teammate=False, keeper=True),
    ]


def _move(p: FreezeFramePlayer, *, x=None, y=None) -> FreezeFramePlayer:
    return FreezeFramePlayer(
        x=p.x if x is None else x,
        y=p.y if y is None else y,
        teammate=p.teammate,
        actor=p.actor,
        keeper=p.keeper,
    )


@given(frames())
@settings(max_examples=300)
def test_law11_always_consistent_with_geometry(frame) -> None:
    """The rule engine never contradicts the received decision, and (after the halfway-line
    fix) its own derivation matches the geometry on every frame."""
    geo = compute_offside(frame)
    proof = law11.prove(
        is_offside=geo.is_offside,
        margin_meters=geo.margin_meters,
        beyond_defender=geo.beyond_defender,
        beyond_ball=geo.beyond_ball,
        attacker_x=geo.attacker_x,
    )
    assert proof.consistent_with_decision is True
    assert proof.derived_offside == geo.is_offside


@given(frames())
@settings(max_examples=200)
def test_is_offside_requires_opponent_half(frame) -> None:
    """Law 11.1: an offside position is impossible outside the opponents' half."""
    geo = compute_offside(frame)
    if geo.is_offside:
        assert geo.attacker_x > HALFWAY_X


@given(frames())
@settings(max_examples=200)
def test_metamorphic_lateral_mirror_is_invariant(frame) -> None:
    """Mirroring the pitch sideways (y -> 80 - y) must not change an offside call."""
    mirrored = [_move(p, y=80.0 - p.y) for p in frame]
    a, b = compute_offside(frame), compute_offside(mirrored)
    assert a.is_offside == b.is_offside
    assert a.margin_meters == b.margin_meters
    assert a.attacker_x == b.attacker_x


@given(frames(), st.floats(min_value=-15.0, max_value=15.0, allow_nan=False))
@settings(max_examples=200)
def test_metamorphic_x_translation_preserves_margin(frame, dx) -> None:
    """The margin is relative (attacker minus the line), so a uniform x-shift cannot change it."""
    shifted = [_move(p, x=p.x + dx) for p in frame]
    assert compute_offside(shifted).margin_meters == compute_offside(frame).margin_meters


@given(frames(), st.randoms(use_true_random=True))
@settings(max_examples=200)
def test_metamorphic_permutation_is_invariant(frame, rng) -> None:
    """The verdict depends on positions, not on the order players appear in the frame."""
    shuffled = frame[:]
    rng.shuffle(shuffled)
    assert compute_offside(shuffled) == compute_offside(frame)
