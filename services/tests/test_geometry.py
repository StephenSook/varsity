import pytest

from app.geometry import (
    METERS_PER_UNIT,
    FreezeFramePlayer,
    compute_offside,
    second_last_opponent_x,
)


def _frame(
    attacker_x: float, second_last_def_x: float, keeper_x: float = 119.0
) -> list[FreezeFramePlayer]:
    """A minimal synthetic freeze-frame, attack left-to-right toward x=120."""
    return [
        FreezeFramePlayer(x=attacker_x, y=40.0, teammate=True, actor=False),
        FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True),  # the passer
        FreezeFramePlayer(x=second_last_def_x, y=42.0, teammate=False),
        FreezeFramePlayer(x=keeper_x, y=40.0, teammate=False, keeper=True),
    ]


def test_offside_attacker_ahead_of_line() -> None:
    r = compute_offside(_frame(100.0, 98.0))
    assert r.is_offside is True
    assert r.offside_line_x == 98.0
    # 2 units ahead, StatsBomb yards -> metres (1 yd = 0.9144 m) = 1.83 m
    assert r.margin_meters == pytest.approx(2.0 * METERS_PER_UNIT, abs=0.01)


def test_onside_attacker_behind_line() -> None:
    r = compute_offside(_frame(95.0, 98.0))
    assert r.is_offside is False
    assert r.margin_meters < 0


def test_not_offside_when_behind_ball() -> None:
    # Ahead of the defender line but behind the ball is not an offside position, and the
    # narrated margin is measured against the ball (the binding reference), so it is negative.
    r = compute_offside(_frame(100.0, 98.0), ball_x=110.0)
    assert r.beyond_defender is True
    assert r.beyond_ball is False
    assert r.is_offside is False
    assert r.reference_x == 110.0
    assert r.margin_meters < 0  # behind the ball reference -> onside, never a positive "ahead"


def test_exactly_level_is_onside() -> None:
    # Level with the second-to-last opponent is onside (Law 11), and never "offside by 0.00 m".
    r = compute_offside(_frame(98.0, 98.0))
    assert r.beyond_defender is False
    assert r.is_offside is False
    assert r.margin_meters == pytest.approx(0.0, abs=0.001)


def test_own_half_attacker_is_not_offside() -> None:
    # Ahead of the second-to-last opponent but in his own half: cannot be offside (halfway gate).
    r = compute_offside(_frame(55.0, 45.0))
    assert r.beyond_defender is True
    assert r.is_offside is False


def test_keeper_not_deepest_uses_second_deepest_opponent() -> None:
    # A high keeper: the offside line is the second-deepest OPPONENT (an outfielder here),
    # because the keeper is intentionally kept in the candidate pool.
    frame = [
        FreezeFramePlayer(x=95.0, y=40.0, teammate=True),
        FreezeFramePlayer(x=30.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=100.0, y=40.0, teammate=False),  # deepest outfielder
        FreezeFramePlayer(x=90.0, y=41.0, teammate=False),  # second-deepest -> the line
        FreezeFramePlayer(x=75.0, y=40.0, teammate=False, keeper=True),  # high keeper
    ]
    r = compute_offside(frame)
    assert r.offside_line_x == 90.0
    assert second_last_opponent_x(frame) == 90.0


def test_needs_two_opponents() -> None:
    frame = [
        FreezeFramePlayer(x=100.0, y=40.0, teammate=True),
        FreezeFramePlayer(x=119.0, y=40.0, teammate=False, keeper=True),
    ]
    with pytest.raises(ValueError):
        second_last_opponent_x(frame)
