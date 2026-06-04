"""GUM uncertainty budget + Bayesian / information-theoretic confidence for the offside margin.

The rigorous superset of the "VARSITY's Call" band (``uncertainty.py``). It expresses the
margin's uncertainty the way international metrology does (BIPM JCGM 100:2008, the GUM), states a
Bayesian credible interval and the Shannon entropy of the call in bits, and cross-checks with
Monte-Carlo propagation (GUM Supplement 1, JCGM 101:2008). It DESCRIBES the precision of the
received decision's geometry; it never adjudicates.

THE HONEST TWO-REGIME PICTURE. Our coordinates are a single broadcast-annotated (x, y) per player
from StatsBomb 360 - not limb-level optical tracking. So there are two regimes:
- OPTICAL-EQUIVALENT (optimistic): if this were TRACAB-grade optical tracking (~9 cm/player, Linke
  et al., PLOS ONE 2020), the margin would be good to ~13 cm - the band ``uncertainty.py`` reports.
- BROADCAST-ANNOTATION (honest): on the single annotated point we actually have, the Type-B
  coordinate uncertainty is far larger. The homography systematic error largely CANCELS in the
  differential margin (both players come from the same frame), but the residual plus the
  body-anchor shape uncertainty (IFAB Law 11 measures the furthest-forward body part, not the
  annotated point) give an honest expanded uncertainty of ~1 m at 95% coverage. VARSITY reports
  the honest regime and refuses to pretend to centimetre precision on coarse data.

The Gaussian noise model is the maximum-entropy choice given only a known variance (Jaynes,
Phys. Rev. 106:620, 1957; Cover & Thomas, Thm 8.6.5; GUM Supplement 1). The margin-to-probability
map P = Phi(m / sigma_m) is the Boltzmann/softmax at temperature T = sigma_m / 1.7
(Phi ~= logistic(1.7 x); Guo, Pleiss, Sun & Weinberger, ICML 2017).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from app.uncertainty import normal_cdf

# --- The Type-B coordinate-uncertainty budget. These are DOCUMENTED, defensible estimates, NOT a
#     published StatsBomb spec (which does not exist). Triangulated from the broadcast-CV tracking
#     literature (Cranga et al. 2025, position RMSE 1.68-16.39 m across providers on a 2022 World
#     Cup match), SciSports (annotations "several meters ... off"), and StatsBomb's homography
#     article. The differential margin is much tighter than the absolute coordinate because the
#     same-frame homography error cancels (correlation r). ---
U_COORD_BROADCAST_M = 0.60  # per-coordinate Type-B std for a broadcast-annotated point (absolute)
HOMOGRAPHY_CORRELATION = 0.70  # r: same-frame homography systematic error cancels in the difference
U_SHAPE_M = 0.30  # body-anchor: Law 11 furthest-forward part vs the annotated point
K_COVERAGE = 2.0  # GUM coverage factor for ~95% under the normal approximation

# Optical-tracking-equivalent reference (the optimistic regime), for the honest comparison.
U_COORD_OPTICAL_M = 0.09  # TRACAB Gen4 per-player RMSE (Linke et al., PLOS ONE 2020)


def combined_position_uncertainty(u_a: float, u_d: float, r: float) -> float:
    """GUM law of propagation for m = x_a - x_d with correlation r:
    u_c^2 = u_a^2 + u_d^2 - 2*r*u_a*u_d (the cross term shrinks the differential)."""
    return math.sqrt(max(u_a**2 + u_d**2 - 2.0 * r * u_a * u_d, 0.0))


def margin_standard_uncertainty_m() -> float:
    """Combined standard uncertainty u_c on the margin: correlated position + body-anchor shape."""
    u_pos = combined_position_uncertainty(
        U_COORD_BROADCAST_M, U_COORD_BROADCAST_M, HOMOGRAPHY_CORRELATION
    )
    return math.sqrt(u_pos**2 + U_SHAPE_M**2)


# The honest broadcast-regime margin standard uncertainty (~0.55 m).
SIGMA_MARGIN_GUM_M = round(margin_standard_uncertainty_m(), 3)
# The optical-equivalent margin sigma (~0.13 m), for the honest comparison.
SIGMA_MARGIN_OPTICAL_M = round(
    combined_position_uncertainty(U_COORD_OPTICAL_M, U_COORD_OPTICAL_M, 0.0), 3
)


def entropy_bits(p: float) -> float:
    """Shannon binary entropy H2(p) in bits: 1 bit at p=0.5, 0 bits at p in {0, 1}."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def verbosity_tier(h_bits: float) -> str:
    """Entropy-driven narration length: more bits of uncertainty -> more words."""
    if h_bits < 0.2:
        return "concise"
    if h_bits < 0.7:
        return "standard"
    return "rich"


def temperature_m(sigma_m: float) -> float:
    """The Boltzmann/softmax temperature T for which logistic(m/T) ~= Phi(m/sigma_m)."""
    return round(sigma_m / 1.7, 3)


def monte_carlo_p_offside(
    margin_m: float, sigma_m: float, *, draws: int = 10000, seed: int = 11
) -> tuple[float, tuple[float, float], int]:
    """GUM-S1 Monte-Carlo: P(offside) = fraction of noise-perturbed margins beyond the line, with a
    Wilson 95% interval on the simulation proportion."""
    rng = random.Random(seed)
    beyond = sum(1 for _ in range(draws) if (margin_m + rng.gauss(0.0, sigma_m)) > 0.0)
    p = beyond / draws
    z = 1.96
    denom = 1.0 + z * z / draws
    centre = (p + z * z / (2 * draws)) / denom
    half = (z * math.sqrt(p * (1 - p) / draws + z * z / (4 * draws * draws))) / denom
    return p, (round(centre - half, 4), round(centre + half, 4)), beyond


@dataclass(frozen=True)
class UncertaintyBudget:
    margin_m: float
    sigma_margin_m: float  # honest broadcast-regime combined standard uncertainty u_c
    expanded_uncertainty_m: float  # U = k * u_c (95% coverage)
    coverage_interval_m: tuple[float, float]  # m +/- U (GUM coverage interval)
    credible_interval_m: tuple[float, float]  # m +/- 1.96*sigma (Bayesian 95%)
    p_offside: float  # Phi(m / sigma_m): the data's support for the offside hypothesis
    entropy_bits: float
    verbosity: str
    temperature_m: float
    mc_p_offside: float
    mc_ci: tuple[float, float]
    mc_draws_beyond: int
    optical_equivalent_sigma_m: float  # the "if we had optical tracking" comparison
    straddles_zero: bool  # the coverage interval contains 0 -> honestly too close to call
    note: str


def _note(b: dict) -> str:
    lo, hi = b["coverage_interval_m"]
    if b["straddles_zero"]:
        return (
            f"Central margin {b['margin_m']:+.2f} m, but the honest 95% coverage interval "
            f"[{lo:+.2f}, {hi:+.2f}] m straddles the line: on our single broadcast-annotated point "
            "this is too close to call, so VARSITY trusts the official's decision."
        )
    return (
        f"Central margin {b['margin_m']:+.2f} m, expanded uncertainty "
        f"+/-{b['expanded_uncertainty_m']:.2f} m at 95% GUM coverage "
        f"([{lo:+.2f}, {hi:+.2f}] m). Even at the honest broadcast-data uncertainty the call is "
        "secure; we report the margin to one decimal place, not fake precision."
    )


def budget(
    margin_meters: float,
    *,
    sigma_m: float = SIGMA_MARGIN_GUM_M,
    k: float = K_COVERAGE,
    draws: int = 10000,
) -> UncertaintyBudget:
    """The full GUM + Bayesian + information-theoretic uncertainty budget for a margin."""
    m = round(margin_meters, 3)
    u_c = sigma_m
    big_u = round(k * u_c, 3)
    coverage = (round(m - big_u, 2), round(m + big_u, 2))
    credible = (round(m - 1.96 * u_c, 2), round(m + 1.96 * u_c, 2))
    p_off = normal_cdf(m / u_c) if u_c > 0 else (1.0 if m > 0 else 0.0)
    h = entropy_bits(p_off)
    mc_p, mc_ci, beyond = monte_carlo_p_offside(m, u_c, draws=draws)
    straddles = coverage[0] < 0.0 < coverage[1]
    fields = {
        "margin_m": m,
        "expanded_uncertainty_m": big_u,
        "coverage_interval_m": coverage,
        "straddles_zero": straddles,
    }
    return UncertaintyBudget(
        margin_m=m,
        sigma_margin_m=round(u_c, 3),
        expanded_uncertainty_m=big_u,
        coverage_interval_m=coverage,
        credible_interval_m=credible,
        p_offside=round(p_off, 3),
        entropy_bits=round(h, 3),
        verbosity=verbosity_tier(h),
        temperature_m=temperature_m(u_c),
        mc_p_offside=round(mc_p, 3),
        mc_ci=mc_ci,
        mc_draws_beyond=beyond,
        optical_equivalent_sigma_m=SIGMA_MARGIN_OPTICAL_M,
        straddles_zero=straddles,
        note=_note(fields),
    )


def payload(margin_meters: float) -> dict:
    """The judge-facing JSON for the /uncertainty endpoint + the SSE stage."""
    b = budget(margin_meters)
    return {
        "margin_m": b.margin_m,
        "sigma_margin_m": b.sigma_margin_m,
        "expanded_uncertainty_m": b.expanded_uncertainty_m,
        "coverage_factor_k": K_COVERAGE,
        "coverage_interval_m": list(b.coverage_interval_m),
        "credible_interval_m": list(b.credible_interval_m),
        "p_offside": b.p_offside,
        "entropy_bits": b.entropy_bits,
        "verbosity": b.verbosity,
        "temperature_m": b.temperature_m,
        "monte_carlo": {
            "p_offside": b.mc_p_offside,
            "wilson_ci95": list(b.mc_ci),
            "draws_beyond": b.mc_draws_beyond,
            "draws": 10000,
        },
        "regimes": {
            "broadcast_annotation_sigma_m": b.sigma_margin_m,
            "optical_equivalent_sigma_m": b.optical_equivalent_sigma_m,
        },
        "budget_inputs": {
            "u_coord_broadcast_m": U_COORD_BROADCAST_M,
            "homography_correlation": HOMOGRAPHY_CORRELATION,
            "u_shape_m": U_SHAPE_M,
        },
        "note": b.note,
        "sources": (
            "GUM (BIPM JCGM 100:2008) + Supplement 1 (JCGM 101:2008); Jaynes 1957 (Phys. Rev. "
            "106:620); Shannon binary entropy; Guo et al. 2017 (ICML) temperature scaling. The "
            "coordinate Type-B budget is a documented estimate, not a published StatsBomb spec."
        ),
    }
