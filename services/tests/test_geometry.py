import pytest

from app.geometry import (
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
    # 2 units ahead * (105/120) = 1.75 m
    assert r.margin_meters == pytest.approx(1.75, abs=0.01)


def test_onside_attacker_behind_line() -> None:
    r = compute_offside(_frame(95.0, 98.0))
    assert r.is_offside is False
    assert r.margin_meters < 0


def test_not_offside_when_behind_ball() -> None:
    # Ahead of the defender line but behind the ball is not an offside position.
    r = compute_offside(_frame(100.0, 98.0), ball_x=110.0)
    assert r.beyond_defender is True
    assert r.beyond_ball is False
    assert r.is_offside is False


def test_needs_two_opponents() -> None:
    frame = [
        FreezeFramePlayer(x=100.0, y=40.0, teammate=True),
        FreezeFramePlayer(x=119.0, y=40.0, teammate=False, keeper=True),
    ]
    with pytest.raises(ValueError):
        second_last_opponent_x(frame)
