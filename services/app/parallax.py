"""Camera-parallax explainer: why broadcast offside often LOOKS wrong.

A broadcast camera is never perfectly in line with the offside line, and it carries a small
residual pointing error even after calibration. Projective geometry says a point at distance
D from a camera whose orientation is off by a tiny angle d appears shifted by about D * tan(d)
across the image. Over the tens of metres from a main camera to a penalty-area incident, even
a fraction of a degree moves where the offside line APPEARS to cross the pitch by tens of
centimetres - comparable to a tight call's own margin. That is why a sighted viewer, judging
from one broadcast angle, can disagree with a correct VAR call.

This module estimates that apparent shift purely to EXPLAIN the disagreement a blind fan may
hear from sighted commentary. It never recomputes, second-guesses, or adjudicates the
decision: VARSITY uses the real tracked positions on the pitch; the camera's view is the thing
being explained, not a new verdict.

Bounded, illustrative estimate with stated assumptions, computed from the attacker's REAL
distance to a typical main-camera position in the freeze-frame. Sources: the Premier League's
own VAR offside-line explainer ("unless a broadcast camera is perfectly in line with the last
defender, the camera angle can make him appear to be further back or forward than he is"; and
on roll, "the vertical line can appear to lean to one side"); Soltani, The Conversation /
University of Bath 2022, a motion-capture study of perceived offside error by camera angle;
ESPN VAR Review on parallax ("the difference in the apparent position along different lines of
sight").
"""

from __future__ import annotations

import math

from app.geometry import FreezeFramePlayer, most_advanced_attacker, second_last_opponent_x

_X_UNITS_TO_METERS = 105.0 / 120.0  # StatsBomb pitch length -> metres
_Y_UNITS_TO_METERS = 68.0 / 80.0  # StatsBomb pitch width -> metres

# A typical main broadcast camera: at the halfway line, set back beyond the near touchline and
# elevated (metres; x along the 105 m pitch, y across the 68 m pitch, z height).
_CAMERA_M = (52.5, -25.0, 18.0)
# Residual pointing error a calibrated broadcast camera still carries (degrees). A fifth of a
# degree is a conservative, illustrative figure, not a measured per-camera value.
_RESIDUAL_ANGLE_DEG = 0.2
_MAX_SHIFT_M = 0.6  # bound the illustrative figure to a physically sane range


def estimate(frame: list[FreezeFramePlayer]) -> dict:
    """Apparent broadcast offside-line shift from the attacker's distance to a main camera.

    Returns the camera-to-incident distance (metres), the assumed residual angle, the bounded
    apparent on-screen shift (cm), and a screen-reader sentence explaining the deception.
    """
    attacker = most_advanced_attacker(frame)
    line_x = second_last_opponent_x(frame)
    ax_m = attacker.x * _X_UNITS_TO_METERS
    ay_m = attacker.y * _Y_UNITS_TO_METERS
    cx, cy, cz = _CAMERA_M
    distance_m = round(math.sqrt((ax_m - cx) ** 2 + (ay_m - cy) ** 2 + cz**2), 1)

    shift_m = min(distance_m * math.tan(math.radians(_RESIDUAL_ANGLE_DEG)), _MAX_SHIFT_M)
    apparent_shift_cm = round(shift_m * 100)
    # depth of the offside line down the pitch (context only; never re-adjudicates)
    line_x_m = round(line_x * _X_UNITS_TO_METERS, 1)
    note = (
        f"This incident is about {distance_m} m from a typical main camera. Even a calibrated "
        f"broadcast camera carries a small residual angle, and over that distance roughly a "
        f"fifth of a degree moves where the offside line APPEARS to cross the pitch by about "
        f"{apparent_shift_cm} cm, which is why sighted commentary judging from one angle can "
        "disagree with a correct call. VARSITY uses the real tracked positions, not the "
        "camera's view."
    )
    return {
        "camera_distance_m": distance_m,
        "line_depth_m": line_x_m,
        "residual_angle_deg": _RESIDUAL_ANGLE_DEG,
        "apparent_shift_cm": apparent_shift_cm,
        "note": note,
    }


def parallax_stage(frame: list[FreezeFramePlayer]) -> dict:
    """SSE stage payload for the camera-parallax explainer."""
    return {"stage": "parallax", **estimate(frame)}
