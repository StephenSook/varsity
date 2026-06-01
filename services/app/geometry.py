"""Offside-margin geometry over StatsBomb 360 freeze-frames.

The StatsBomb pitch is 120 x 80 units and the attack direction is ALWAYS
left-to-right, so the attacking team is shooting toward the goal line at x = 120
in every frame. Every margin computed here assumes that normalization. Do not
feed raw multi-direction coordinates without standardizing them first, or the
margins will compute backwards.

Convention:
- ``teammate=True`` marks a player on the same side as the actor (the attacking
  side that just played the ball).
- The "second-to-last opponent" is the offside line. Opponents defend the goal at
  x = 120, so the last opponent is the one with the largest x (often the keeper)
  and the second-last is the next-largest x.
- ``margin_meters`` is signed and measured against the second-to-last opponent:
  positive means the attacker is ahead of the line (the offside side).
"""

from __future__ import annotations

from dataclasses import dataclass

PITCH_LENGTH_UNITS = 120.0
PITCH_LENGTH_METERS = 105.0
_UNITS_TO_METERS = PITCH_LENGTH_METERS / PITCH_LENGTH_UNITS


@dataclass(frozen=True)
class FreezeFramePlayer:
    x: float
    y: float
    teammate: bool
    actor: bool = False
    keeper: bool = False


@dataclass(frozen=True)
class OffsideResult:
    is_offside: bool
    margin_meters: float
    offside_line_x: float
    attacker_x: float
    beyond_defender: bool
    beyond_ball: bool


def _attackers(frame: list[FreezeFramePlayer]) -> list[FreezeFramePlayer]:
    return [p for p in frame if p.teammate]


def _defenders(frame: list[FreezeFramePlayer]) -> list[FreezeFramePlayer]:
    return [p for p in frame if not p.teammate]


def second_last_opponent_x(frame: list[FreezeFramePlayer]) -> float:
    """X of the second-to-last opponent (the offside line), attack left-to-right."""
    defenders = _defenders(frame)
    if len(defenders) < 2:
        raise ValueError("need at least two opponents to define an offside line")
    xs = sorted((p.x for p in defenders), reverse=True)
    return xs[1]


def most_advanced_attacker(
    frame: list[FreezeFramePlayer], *, exclude_actor: bool = True
) -> FreezeFramePlayer:
    """The attacker nearest the opponents' goal line (largest x)."""
    attackers = _attackers(frame)
    if exclude_actor:
        non_actor = [p for p in attackers if not p.actor]
        attackers = non_actor or attackers
    if not attackers:
        raise ValueError("no attackers in freeze-frame")
    return max(attackers, key=lambda p: p.x)


def compute_offside(
    frame: list[FreezeFramePlayer], *, ball_x: float | None = None
) -> OffsideResult:
    """Compute whether the most advanced attacker is in an offside position.

    A player is offside if any scorable part of the body is nearer the goal line
    than BOTH the ball and the second-to-last opponent. ``margin_meters`` is the
    distance ahead of the second-to-last opponent (the narrated number).
    """
    line_x = second_last_opponent_x(frame)
    attacker = most_advanced_attacker(frame)
    margin_units = attacker.x - line_x
    beyond_defender = margin_units > 0
    beyond_ball = True if ball_x is None else attacker.x > ball_x
    return OffsideResult(
        is_offside=beyond_defender and beyond_ball,
        margin_meters=round(margin_units * _UNITS_TO_METERS, 2),
        offside_line_x=line_x,
        attacker_x=attacker.x,
        beyond_defender=beyond_defender,
        beyond_ball=beyond_ball,
    )
