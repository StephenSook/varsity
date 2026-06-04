"""Descriptive computational geometry over the freeze-frame.

Treats the defensive line as a geometric OBJECT and adds narratable scalars for a blind fan: its
tilt (a robust Theil-Sen fit), its depth/thickness (closed-form 2D PCA), and its lateral spread,
plus a provably-correct "ahead-of-line" predicate (an exact-rational orient2d, the guarantee that
Shewchuk's adaptive-precision predicates give, Discrete & Comp. Geometry 18(3):305-363, 1997).

These DESCRIBE the spatial context of the received decision. The offside line itself stays the
perpendicular through the second-last opponent (Law 11); this never redefines it or re-adjudicates.

Considered and REJECTED (they need data we do not have, and saying so is the point): Voronoi
space-control (needs scipy/shapely + full-pitch clipping; the lateral-width + thickness scalars
carry the narratable value without the dependency), persistent homology / TDA (a ~14-point
freeze-frame is far too sparse for a meaningful persistence diagram), and tropical / information /
Morse geometry (each needs trajectories, velocities, or populations of frames, not one instant).
The whole module is pure Python (math + fractions): no scipy, no sklearn, no numpy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from statistics import median

from app.geometry import (
    METERS_PER_UNIT,
    FreezeFramePlayer,
    _defenders,
    most_advanced_attacker,
    second_last_opponent_x,
)


def orient2d_sign(
    ax: float, ay: float, bx: float, by: float, cx: float, cy: float
) -> int:
    """Sign of twice the signed area of triangle (a, b, c), in EXACT rational arithmetic so it is
    provably immune to floating-point cancellation for nearly-collinear inputs (the guarantee of
    Shewchuk's adaptive-precision predicates, 1997). +1 = c left of a->b, -1 = right, 0 = collinear
    (level). It certifies the SIGN the geometry intends, never an IFAB verdict."""
    det = (Fraction(bx) - Fraction(ax)) * (Fraction(cy) - Fraction(ay)) - (
        Fraction(by) - Fraction(ay)
    ) * (Fraction(cx) - Fraction(ax))
    return (det > 0) - (det < 0)


def ahead_of_line_sign(frame: list[FreezeFramePlayer]) -> int:
    """Exact sign of 'the evaluated attacker is ahead of the vertical second-last-opponent line'.
    The line is the points (line_x, 0)->(line_x, 80); attack is left-to-right, so a point with
    x > line_x is to the right of the upward line (negative orient2d), which we flip to +1 = ahead.
    """
    line_x = second_last_opponent_x(frame)
    a = most_advanced_attacker(frame)
    return -orient2d_sign(line_x, 0.0, line_x, 80.0, a.x, a.y)


def _back_line(frame: list[FreezeFramePlayer]) -> list[FreezeFramePlayer]:
    """The outfield back line: opponents excluding the keeper (deep, not part of the line shape).
    Falls back to all opponents if too few outfielders to fit a line."""
    opponents = _defenders(frame)
    outfield = [d for d in opponents if not d.keeper]
    return outfield if len(outfield) >= 2 else opponents


def _pca_thickness_m(points: list[FreezeFramePlayer]) -> float:
    """Defensive-line depth = sqrt of the MINOR eigenvalue of the 2D position covariance (the
    spread perpendicular to the principal axis), in metres. Closed-form 2x2 eigenvalues."""
    n = len(points)
    mx = sum(p.x for p in points) / n
    my = sum(p.y for p in points) / n
    sxx = sum((p.x - mx) ** 2 for p in points) / n
    syy = sum((p.y - my) ** 2 for p in points) / n
    sxy = sum((p.x - mx) * (p.y - my) for p in points) / n
    disc = math.sqrt(max(((sxx - syy) / 2) ** 2 + sxy**2, 0.0))
    lam_min = max((sxx + syy) / 2 - disc, 0.0)
    return round(math.sqrt(lam_min) * METERS_PER_UNIT, 2)


def _theil_sen_tilt_deg(points: list[FreezeFramePlayer]) -> float:
    """Robust defensive-line tilt: the Theil-Sen median of pairwise slopes dx/dy (the line is
    near-vertical in attack coordinates, so x is regressed on y), as degrees from the goal line.
    Theil-Sen has a ~29.3% breakdown point, so one out-of-position defender does not swing it."""
    slopes = [
        (points[i].x - points[j].x) / (points[i].y - points[j].y)
        for i in range(len(points))
        for j in range(i + 1, len(points))
        if abs(points[i].y - points[j].y) > 1e-9
    ]
    if not slopes:
        return 0.0
    return round(math.degrees(math.atan(median(slopes))), 1)


def _lateral_width_m(points: list[FreezeFramePlayer]) -> float:
    ys = [p.y for p in points]
    return round((max(ys) - min(ys)) * METERS_PER_UNIT, 1)


@dataclass(frozen=True)
class LineDescriptors:
    n_defenders: int  # visible outfield opponents fitted (not just a back four)
    tilt_deg: float  # robust Theil-Sen tilt of the defensive line from the goal line
    thickness_m: float  # defensive-line depth (PCA minor axis)
    lateral_width_m: float  # the line's lateral spread
    ahead_of_line_sign: int  # exact orient2d sign for the evaluated attacker
    note: str


def describe(frame: list[FreezeFramePlayer]) -> LineDescriptors:
    line = _back_line(frame)
    tilt = _theil_sen_tilt_deg(line)
    thickness = _pca_thickness_m(line)
    width = _lateral_width_m(line)
    ahead = ahead_of_line_sign(frame)
    note = (
        f"The {len(line)} visible defenders formed a line {abs(tilt):.1f} degrees "
        f"{'tilted' if abs(tilt) >= 1 else 'level'} to the goal line, "
        f"{thickness:.2f} m deep and {width:.1f} m wide."
    )
    return LineDescriptors(
        n_defenders=len(line),
        tilt_deg=tilt,
        thickness_m=thickness,
        lateral_width_m=width,
        ahead_of_line_sign=ahead,
        note=note,
    )


def payload(frame: list[FreezeFramePlayer]) -> dict:
    d = describe(frame)
    return {
        "n_defenders": d.n_defenders,
        "tilt_deg": d.tilt_deg,
        "thickness_m": d.thickness_m,
        "lateral_width_m": d.lateral_width_m,
        "ahead_of_line_sign": d.ahead_of_line_sign,
        "note": d.note,
        "method": (
            "Theil-Sen robust tilt (29.3% breakdown), closed-form 2D PCA thickness, and an "
            "exact-rational orient2d 'ahead-of-line' predicate (Shewchuk 1997). Describes the "
            "defensive line; the offside line stays the Law-11 perpendicular through the "
            "second-last opponent."
        ),
    }
