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

from app.uncertainty import normal_cdf, quantify


def _withhold(margin_meters: float, straddles_zero: bool) -> bool:
    """Speak the 'too close to call, trust the official' line ONLY when the broadcast-data coverage
    interval straddles the line AND the calibrated band (the SAME decision the spoken verdict uses)
    also reads the call as very tight. This keeps the two uncertainty layers telling one story: a
    confident verdict is never paired with a 'too close to call' withholding for a margin the band
    reads as clear or marginal."""
    return straddles_zero and quantify(margin_meters).band == "very tight"

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
    if _withhold(b["margin_m"], b["straddles_zero"]):
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


# IPCC AR6 calibrated language WITH the numeric range. Budescu et al. (2009 Psych. Science;
# 2014 Nature Climate Change) showed lay listeners under-interpret the words toward 50%, so we
# pair the word with the percentage in spoken text - the documented mitigation, and exactly right
# for a blind-fan audience who cannot see a number on screen.
_IPCC_BANDS: list[tuple[float, str, str]] = [
    (0.99, "virtually certain", "99 to 100 percent"),
    (0.95, "extremely likely", "95 to 100 percent"),
    (0.90, "very likely", "90 to 95 percent"),
    (0.66, "likely", "66 to 90 percent"),
    (0.50, "more likely than not", "50 to 66 percent"),
]


def ipcc_hedge(p: float) -> tuple[str, str]:
    """Map a probability to the IPCC verbal hedge AND its numeric range."""
    for threshold, word, rng in _IPCC_BANDS:
        if p >= threshold:
            return word, rng
    return "more likely than not", "50 to 66 percent"


def spoken_narration(
    margin_meters: float, is_offside: bool, *, sigma_m: float = SIGMA_MARGIN_GUM_M
) -> str:
    """A DETERMINISTIC spoken line for the aria-live verdict, length set by the entropy tier. The
    numbers come from the geometry, never from the LLM (the spoken uncertainty must not be a model
    confabulation). It describes the data's support for the received call; it never adjudicates."""
    b = budget(margin_meters, sigma_m=sigma_m)
    p = b.p_offside if is_offside else (1.0 - b.p_offside)
    word, rng = ipcc_hedge(p)
    verdict = "offside" if is_offside else "onside"
    lo, hi = b.coverage_interval_m
    if _withhold(margin_meters, b.straddles_zero):
        return (
            f"This is a close call, carrying {b.entropy_bits:.2f} bits of uncertainty. On the "
            f"single broadcast point we have, the 95 percent coverage interval runs from "
            f"{lo:+.1f} to {hi:+.1f} metres, straddling the line, so VARSITY trusts the official's "
            f"{verdict} call."
        )
    # The coverage interval is always spoken (the headline honest number); the entropy tier adds
    # the close-call detail above. A clear call is short; a close call gets the full treatment.
    return (
        f"On the data this is {word}, {rng}, {verdict}. The margin's 95 percent coverage interval "
        f"runs from {lo:+.1f} to {hi:+.1f} metres."
    )


def student_t_sensitivity(
    margin_meters: float,
    *,
    sigma_m: float = SIGMA_MARGIN_GUM_M,
    nu: int = 5,
    draws: int = 10000,
    seed: int = 11,
) -> dict:
    """Heavy-tail robustness check (the report's recommended caveat): re-run P(offside) with a
    Student-t(nu) noise model scaled to the SAME sigma, and report whether the probability shifts.
    If it barely moves, the Gaussian maximum-entropy choice is robust here; a large shift would be
    honest to surface. Pure Python (t = Z / sqrt(chi2(nu)/nu), no scipy)."""
    gaussian_p = normal_cdf(margin_meters / sigma_m) if sigma_m > 0 else float(margin_meters > 0)
    rng = random.Random(seed)
    scale = sigma_m / math.sqrt(nu / (nu - 2)) if nu > 2 else sigma_m
    beyond = 0
    for _ in range(draws):
        z = rng.gauss(0.0, 1.0)
        chi2 = rng.gammavariate(nu / 2.0, 2.0)
        t = z / math.sqrt(chi2 / nu)
        if margin_meters + t * scale > 0.0:
            beyond += 1
    t_p = beyond / draws
    shift_pp = round((t_p - gaussian_p) * 100, 2)
    return {
        "nu": nu,
        "gaussian_p_offside": round(gaussian_p, 3),
        "student_t_p_offside": round(t_p, 3),
        "shift_percentage_points": shift_pp,
        "robust": abs(shift_pp) < 2.0,
    }


def fitted_temperature(*, sigma_m: float = SIGMA_MARGIN_GUM_M) -> dict:
    """Fit the Boltzmann temperature T so the softmax sigmoid(m/T) best reproduces the Gaussian
    posterior Phi(m/sigma) over a grid of margins (temperature scaling, Guo et al. 2017). It
    recovers the closed-form T = sigma/1.7, a self-consistency receipt: the fitted and analytic
    temperatures agree. Deterministic (golden-section over a fixed grid)."""
    grid = [i * 0.05 for i in range(-40, 41)]
    target = [normal_cdf(m / sigma_m) for m in grid]

    def mse(t: float) -> float:
        return sum((1.0 / (1.0 + math.exp(-m / t)) - q) ** 2 for m, q in zip(grid, target)) / len(
            grid
        )

    lo, hi = 0.1, 0.6
    gr = (math.sqrt(5) - 1) / 2
    c, d = hi - gr * (hi - lo), lo + gr * (hi - lo)
    for _ in range(60):
        if mse(c) < mse(d):
            hi = d
        else:
            lo = c
        c, d = hi - gr * (hi - lo), lo + gr * (hi - lo)
    fitted = round((lo + hi) / 2, 3)
    closed = temperature_m(sigma_m)
    return {
        "fitted_temperature_m": fitted,
        "closed_form_temperature_m": closed,
        "agree": abs(fitted - closed) < 0.05,
    }


def payload(margin_meters: float, *, is_offside: bool = False, extended: bool = False) -> dict:
    """The judge-facing JSON for the /uncertainty endpoint + the SSE stage. ``extended`` adds the
    heavier robustness receipts (Student-t sensitivity + the fitted-temperature self-consistency)
    for the on-demand endpoint; the per-stream SSE stage leaves them off to stay fast."""
    b = budget(margin_meters)
    out = {
        "spoken": spoken_narration(margin_meters, is_offside),
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
    if extended:
        out["student_t_sensitivity"] = student_t_sensitivity(margin_meters)
        out["fitted_temperature"] = fitted_temperature()
    return out
