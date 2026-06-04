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
import random
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

# StatsBomb's 120 x 80 grid is in yards; the pitch is 120 long, 80 wide.
_PITCH_LEN = 120.0
_PITCH_WID = 80.0
_DEFENDER_REACH_YD = 3.0  # how far a defender could plausibly reach in the freeze instant


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


def _convex_hull(points: list[FreezeFramePlayer]) -> list[tuple[float, float]]:
    """Andrew's monotone-chain convex hull (the report's named structure), pure Python."""
    pts = sorted({(p.x, p.y) for p in points})
    if len(pts) < 3:
        return pts

    def cross(o: tuple, a: tuple, b: tuple) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _hull_area_m2(points: list[FreezeFramePlayer]) -> float:
    """Shoelace area of the defenders' convex hull, in square metres."""
    hull = _convex_hull(points)
    if len(hull) < 3:
        return 0.0
    a = 0.0
    for i in range(len(hull)):
        x1, y1 = hull[i]
        x2, y2 = hull[(i + 1) % len(hull)]
        a += x1 * y2 - x2 * y1
    return round(abs(a) / 2.0 * METERS_PER_UNIT**2, 1)


def _free_space_behind_line_m2(
    frame: list[FreezeFramePlayer], line_x: float, *, samples: int = 4000, seed: int = 11
) -> float:
    """A seeded Monte-Carlo estimate of the space BEHIND the offside line that no defender could
    reach first (farther than a defender's reach from every opponent), in square metres. This is
    the vanishing-speed Voronoi-lite scalar (correct for an instantaneous frame, Efthimiou 2021)
    without the scipy/shapely dependency."""
    defenders = [(d.x, d.y) for d in _defenders(frame)]
    if line_x >= _PITCH_LEN or not defenders:
        return 0.0
    rng = random.Random(seed)
    region_yd2 = (_PITCH_LEN - line_x) * _PITCH_WID
    r2 = _DEFENDER_REACH_YD**2
    free = 0
    for _ in range(samples):
        rx = rng.uniform(line_x, _PITCH_LEN)
        ry = rng.uniform(0.0, _PITCH_WID)
        if all((rx - dx) ** 2 + (ry - dy) ** 2 > r2 for dx, dy in defenders):
            free += 1
    return round(free / samples * region_yd2 * METERS_PER_UNIT**2, 1)


def _line_step_m(line: list[FreezeFramePlayer]) -> float:
    """How STEPPED the back line was: the x-spread of the three deepest defenders, in metres (the
    report's 'the right-back was 4 m deeper' descriptor, without a fragile Delaunay alpha-shape)."""
    xs = sorted((d.x for d in line), reverse=True)[:3]
    return round((max(xs) - min(xs)) * METERS_PER_UNIT, 1) if len(xs) >= 2 else 0.0


@dataclass(frozen=True)
class LineDescriptors:
    n_defenders: int  # visible outfield opponents fitted (not just a back four)
    tilt_deg: float  # robust Theil-Sen tilt of the defensive line from the goal line
    thickness_m: float  # defensive-line depth (PCA minor axis)
    lateral_width_m: float  # the line's lateral spread
    ahead_of_line_sign: int  # exact orient2d sign for the evaluated attacker
    hull_area_m2: float  # convex-hull footprint of the defensive block
    free_space_behind_line_m2: float  # space behind the line no defender could reach first
    line_step_m: float  # how stepped the back line was (deepest-3 x-spread)
    note: str


def describe(frame: list[FreezeFramePlayer]) -> LineDescriptors:
    line = _back_line(frame)
    tilt = _theil_sen_tilt_deg(line)
    thickness = _pca_thickness_m(line)
    width = _lateral_width_m(line)
    ahead = ahead_of_line_sign(frame)
    hull_area = _hull_area_m2(_defenders(frame))
    free_space = _free_space_behind_line_m2(frame, second_last_opponent_x(frame))
    step = _line_step_m(line)
    note = (
        f"The {len(line)} visible defenders formed a line {abs(tilt):.1f} degrees "
        f"{'tilted' if abs(tilt) >= 1 else 'level'} to the goal line, {thickness:.2f} m deep and "
        f"{width:.1f} m wide, with {free_space:.0f} square metres of space behind it that no "
        f"defender could reach first."
    )
    return LineDescriptors(
        n_defenders=len(line),
        tilt_deg=tilt,
        thickness_m=thickness,
        lateral_width_m=width,
        ahead_of_line_sign=ahead,
        hull_area_m2=hull_area,
        free_space_behind_line_m2=free_space,
        line_step_m=step,
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
        "hull_area_m2": d.hull_area_m2,
        "free_space_behind_line_m2": d.free_space_behind_line_m2,
        "line_step_m": d.line_step_m,
        "note": d.note,
        "method": (
            "Theil-Sen robust tilt (29.3% breakdown), closed-form 2D PCA thickness, the defenders' "
            "convex hull (monotone chain) + a Monte-Carlo free-space-behind-the-line estimate "
            "(vanishing-speed Voronoi-lite, no scipy), and an exact-rational orient2d "
            "'ahead-of-line' predicate (Shewchuk 1997). Describes the defensive line; the offside "
            "line stays the Law-11 perpendicular through the second-last opponent."
        ),
    }
