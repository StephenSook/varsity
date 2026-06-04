"""Offside-margin geometry over StatsBomb 360 freeze-frames.

StatsBomb standardizes every event onto a 120 x 80 pitch grid whose units are YARDS (the Open
Data spec measures pass length in yards and defines a "switch" as a pass over 40 yards; mplsoccer
converts StatsBomb distances with ``* 0.9144  # yards -> meters``, and the Hudl/StatsBomb live
schema documents z-height in yards on the same 0-120 / 0-80 frame). So a margin in grid units
converts to metres with the international yard, 1 yd = 0.9144 m - NOT by assuming the 120-unit
length spans a 105 m pitch (that double-applies a normalization StatsBomb never performed and
under-states every margin by ~4.3%). See docs/GEOMETRY.md for sources.

The attack direction is ALWAYS left-to-right (the attacking team shoots toward x = 120), a
StatsBomb standardization. This module assumes it; do not feed raw multi-direction coordinates
without standardizing them first, or the margins compute backwards.

This is a COARSE, point-based, ILLUSTRATIVE description of a RECEIVED decision: StatsBomb 360
gives a single (x, y) per visible player (no limbs), so VARSITY cannot and does not reproduce
FIFA SAOT / the Premier League's Dragon limb-level precision. It never re-adjudicates.

Convention:
- ``teammate=True`` marks a player on the actor's (attacking) side.
- The offside line is the second-to-last OPPONENT. The keeper is INTENTIONALLY kept in the
  candidate pool (Law 11: the second-last opponent, whoever that is - usually but not always the
  keeper); do not "fix" this by excluding ``p.keeper``.
- ``margin_meters`` is signed and measured along the x-axis (the goal-line-normal direction; it
  is intentionally NOT a Euclidean distance, which would inflate the margin with irrelevant
  lateral separation) against the binding Law-11 reference: the nearer of the second-to-last
  opponent and the ball. Positive = ahead of the reference (the offside side).
- By default the most-advanced attacker is evaluated; the received decision identifies the
  flagged player, which can be passed as ``target``.
"""

from __future__ import annotations

from dataclasses import dataclass

# StatsBomb's 120 x 80 grid is in yards; convert margins with the international yard.
METERS_PER_UNIT = 0.9144
PITCH_LENGTH_UNITS = 120.0

# A tiny tolerance so an EXACTLY level attacker (float noise at the line) is treated as onside,
# never a self-contradicting "offside by 0.00 m". The cm-scale "too close to call" is handled
# honestly by the uncertainty band (the ~13 cm "VARSITY's Call"), not a hard verdict flip here.
LEVEL_EPS_UNITS = 1e-9

# Attack is always left-to-right, so the opponents' half is x > the midline (Law 11.1:
# an offside position requires being in the opponents' half, excluding the halfway line).
HALFWAY_X = PITCH_LENGTH_UNITS / 2.0  # 60.0


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
    # signed x-distance from the attacker to ``reference_x`` (the BINDING reference, which can be
    # the ball, not always the defender line): read ``reference_x`` / ``offside_line_x`` to read it,
    # never assume margin_meters is "distance past the defender line".
    margin_meters: float
    offside_line_x: float  # the defender line (the Law-11 second-last-opponent perpendicular)
    attacker_x: float
    beyond_defender: bool
    beyond_ball: bool
    reference_x: float = 0.0  # binding Law-11 reference x: nearer of the defender line and the ball


def _attackers(frame: list[FreezeFramePlayer]) -> list[FreezeFramePlayer]:
    return [p for p in frame if p.teammate]


def _defenders(frame: list[FreezeFramePlayer]) -> list[FreezeFramePlayer]:
    return [p for p in frame if not p.teammate]


def second_last_opponent(frame: list[FreezeFramePlayer]) -> FreezeFramePlayer:
    """The second-to-last opponent (the offside line), attack left-to-right.

    The keeper is INTENTIONALLY included in the candidate pool: Law 11 defines the line by the
    second-last opponent whoever that is (usually but not always the keeper). Do not exclude
    ``p.keeper`` - that would compute the second-last OUTFIELDER and misplace the line whenever an
    outfield defender is deeper than the keeper.
    """
    defenders = _defenders(frame)
    if len(defenders) < 2:
        raise ValueError("need at least two opponents to define an offside line")
    return sorted(defenders, key=lambda p: p.x, reverse=True)[1]


def second_last_opponent_x(frame: list[FreezeFramePlayer]) -> float:
    """X of the second-to-last opponent (the offside line), attack left-to-right."""
    return second_last_opponent(frame).x


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
    frame: list[FreezeFramePlayer],
    *,
    ball_x: float | None = None,
    target: FreezeFramePlayer | None = None,
) -> OffsideResult:
    """Compute whether the evaluated attacker is in an offside position.

    A player is offside if any scorable part of the body is nearer the goal line than BOTH the
    ball and the second-to-last opponent. ``margin_meters`` is the signed x-distance from the
    attacker to the BINDING Law-11 reference (the nearer of the second-to-last opponent and the
    ball), so an attacker ahead of the defender line but behind the ball reports a negative
    (onside) margin rather than a misleading positive one. ``target`` is the flagged attacker from
    the received decision; it defaults to the most-advanced attacker.
    """
    line_x = second_last_opponent_x(frame)
    attacker = target or most_advanced_attacker(frame)
    reference_x = line_x if ball_x is None else max(line_x, ball_x)
    margin_units = attacker.x - reference_x
    beyond_defender = (attacker.x - line_x) > LEVEL_EPS_UNITS
    beyond_ball = True if ball_x is None else attacker.x > ball_x
    in_opponent_half = attacker.x > HALFWAY_X
    return OffsideResult(
        is_offside=in_opponent_half and beyond_defender and beyond_ball,
        margin_meters=round(margin_units * METERS_PER_UNIT, 2),
        offside_line_x=line_x,
        attacker_x=attacker.x,
        beyond_defender=beyond_defender,
        beyond_ball=beyond_ball,
        reference_x=reference_x,
    )
