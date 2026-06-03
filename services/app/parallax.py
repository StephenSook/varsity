"""Camera-parallax explainer: why broadcast offside often LOOKS wrong.

A broadcast camera is rarely perfectly in line with the offside line. When it views the
line obliquely, two players at the same position up the pitch but different sideways
(lateral) positions project to different screen positions, so the drawn line skews and a
correct call can look wrong to a sighted viewer. This module estimates that apparent shift
purely to EXPLAIN the disagreement a blind fan may hear from sighted commentary. It never
recomputes, second-guesses, or adjudicates the decision: VARSITY measures the real positions
on the pitch; the camera angle is the thing being explained, not a new verdict.

Illustrative estimate with stated assumptions, computed from the REAL lateral separation
between the attacker and the second-to-last defender in the freeze-frame. A typical main
camera sees the offside line at roughly 30 degrees off-perpendicular, so a sideways gap of
s metres looks like an along-the-line gap of about s * tan(30 deg) on screen.

Sources: the Premier League's own VAR offside-line explainer ("unless a broadcast camera is
perfectly in line with the last defender, the camera angle can make him appear to be further
back or forward than he is"); Soltani, The Conversation / University of Bath 2022, a
motion-capture study of perceived offside error by camera viewing angle; ESPN VAR Review on
parallax ("the difference in the apparent position along different lines of sight").
"""

from __future__ import annotations

import math

from app.geometry import (
    FreezeFramePlayer,
    most_advanced_attacker,
    second_last_opponent,
)

_Y_UNITS_TO_METERS = 68.0 / 80.0  # StatsBomb pitch width (80 units) -> metres
_CAMERA_ANGLE_DEG = 30.0  # typical main-camera obliqueness to the offside line
_PARALLAX_FACTOR = math.tan(math.radians(_CAMERA_ANGLE_DEG))


def estimate(frame: list[FreezeFramePlayer]) -> dict:
    """Apparent broadcast parallax shift from the real lateral player separation.

    Returns the sideways separation (metres), the assumed camera angle, the apparent
    on-screen shift (cm), and a screen-reader sentence explaining the deception.
    """
    attacker = most_advanced_attacker(frame)
    defender = second_last_opponent(frame)
    lateral_m = round(abs(attacker.y - defender.y) * _Y_UNITS_TO_METERS, 1)
    apparent_shift_cm = round(lateral_m * _PARALLAX_FACTOR * 100)
    note = (
        f"The attacker and the second-to-last defender are about {lateral_m} m apart across "
        f"the pitch. A normal main camera, off to one side, can make that sideways gap look "
        f"like an along-the-line gap of roughly {apparent_shift_cm} cm on screen, which is why "
        "sighted commentary sometimes disagrees with a correct call. VARSITY measures the real "
        "positions on the pitch, not the camera's angle."
    )
    return {
        "lateral_separation_m": lateral_m,
        "camera_angle_deg": _CAMERA_ANGLE_DEG,
        "apparent_shift_cm": apparent_shift_cm,
        "note": note,
    }


def parallax_stage(frame: list[FreezeFramePlayer]) -> dict:
    """SSE stage payload for the camera-parallax explainer."""
    return {"stage": "parallax", **estimate(frame)}
