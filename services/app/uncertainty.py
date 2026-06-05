"""Uncertainty quantification for the offside margin - the "VARSITY's Call" band.

The received margin is an estimate. VARSITY consumes a SINGLE manually-annotated (x, y) per
player from StatsBomb 360 (broadcast video), not optical multi-camera tracking, so the honest
1-sigma on the margin is the broadcast-annotation budget (~0.55 m), NOT the optical-tracking
figure. The band drives VARSITY's spoken confidence, its structured p_verdict, and its
within-noise gate off that ONE honest sigma, so every layer tells the same story as the gum.py
budget. The optical-tracking equivalent (~0.13 m) is kept only as the "if we had a 12-camera
SAOT rig" comparison, so the band can never claim a precision the coarse data does not support.
VARSITY DESCRIBES the received decision's sensitivity to measurement noise; it never adjudicates.

Sources: per-player optical RMSE ~9 cm (Linke, Link & Lames, "Football-specific validity of
TRACAB's optical video tracking systems", PLOS ONE 2020, 15(3):e0230179 - Gen4 0.09 m;
corroborated by Blauberger et al., Sensors 2021). The broadcast-annotation Type-B budget is a
DOCUMENTED, defensible estimate (NOT a published StatsBomb spec), triangulated from Cranga et al.
2025 (broadcast-CV position RMSE 1.68-16.39 m across providers), SciSports ("several meters off"),
and StatsBomb's homography article; the same-frame homography systematic error largely CANCELS in
the differential margin, and the body-anchor shape term reflects Law 11 measuring the
furthest-forward body part rather than the single annotated point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

# The closed domains of the two band scales, so a mistyped literal is a type error, not a silent
# miss on the knife-edge ``band == "very tight"`` defer-to-official gate.
Band = Literal["clear", "tight", "very tight"]
ConfidenceBand = Literal["clear", "marginal", "too_close_to_call"]

# --- The HONEST broadcast-annotation budget VARSITY actually consumes. Each input is now anchored
#     to a MEASURED published figure where one exists; the genuinely-unmeasured pieces are flagged
#     Type-B. See docs/UNCERTAINTY_SOURCES.md for the fetch-verified, verbatim-quoted ledger. gum.py
#     imports these primitives, so the band and the GUM budget share ONE source (no drift). ---
# MEASURED-anchored: single-view homography projection error mean 0.65 m (PnLCalib, Gutierrez-Perez
# & Agudo, CVIU 2026, WC14-test) and detected-player RMSE 0.44-1.14 m (Crang et al. 2025, arXiv
# 2508.19477, vs TRACAB Gen5 on a 2022 World Cup match); 0.60 sits at the centre of that range.
U_COORD_BROADCAST_M = 0.60  # per-coordinate std, broadcast-annotated point (MEASURED-anchored)
# TYPE-B (unmeasured): no study measures the same-frame difference correlation for two football
# points. Szulc & Iwanowski 2026 (arXiv 2604.10805) show homography error is range-dependent, so
# the cancellation is PARTIAL; a lower r (wider sigma) is the more conservative reading.
HOMOGRAPHY_CORRELATION = 0.70  # r: same-frame systematic error PARTIALLY cancels in the difference
# Localization floor MEASURED: 8 cm per-joint vs Vicon in a WC stadium (WorldPose, Jiang et al.,
# CVPR 2025) and +/-10 cm broadcast-TV blur (Mather, Perception 2020); FIFA SAOT skeletal X
# threshold <0.10 m. The extra furthest-forward-part SELECTION offset is unmeasured Type-B.
U_SHAPE_M = 0.30  # body-anchor: Law 11 furthest-forward part vs the annotated point (~0.10 + ~0.20)
# Optical-tracking-equivalent reference (the optimistic regime), kept ONLY as the honest
# "if we had a 12-camera SAOT rig" comparison - NOT the uncertainty of our actual data.
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


# The band's default sigma is the HONEST broadcast-regime combined standard uncertainty (~0.55 m),
# so the spoken confidence, the structured p_verdict, and the within-noise gate tell the SAME story
# as the gum.py budget. A 30 cm offside is then honestly "too close to call" on broadcast data,
# while the clear demo call (5.69 m) stays clear; gum.py uses the same value.
SIGMA_MARGIN_M = round(margin_standard_uncertainty_m(), 3)  # ~= 0.553 m
# The optical-equivalent margin sigma (~0.13 m), kept only as the honest "if we had SAOT" reference.
SIGMA_MARGIN_OPTICAL_M = round(
    combined_position_uncertainty(U_COORD_OPTICAL_M, U_COORD_OPTICAL_M, 0.0), 3
)

# The MEASURED-literature ENVELOPE on each input, used by the sensitivity receipt (gum.sigma_
# sensitivity) to show the verdict is robust across the plausible spread, not just the point value.
U_COORD_LO_M = 0.44  # best detected-player RMSE / PnLCalib median (Crang 2025; PnLCalib 2026)
U_COORD_HI_M = 1.14  # worst detected-player RMSE (Crang 2025); broadcast extraction ~1 m (Theiner)
HOMOGRAPHY_CORRELATION_LO = 0.50  # weaker (partial) cancellation - the conservative end
HOMOGRAPHY_CORRELATION_HI = 0.85  # stronger same-frame cancellation - the optimistic end
U_SHAPE_LO_M = 0.10  # measured localization floor only (WorldPose 8 cm / Mather +/-10 cm)
U_SHAPE_HI_M = 0.30  # localization + the unmeasured furthest-forward-part selection offset


def margin_sigma_bounds() -> tuple[float, float]:
    """The MEASURED-literature envelope on the combined margin sigma: the optimistic end (low
    per-point error, strong cancellation, localization-only shape) and the pessimistic end (high
    per-point error, weak cancellation, full shape term). The point estimate SIGMA_MARGIN_M sits
    inside this band; gum.sigma_sensitivity shows the verdict is robust across it."""
    lo = math.sqrt(
        combined_position_uncertainty(U_COORD_LO_M, U_COORD_LO_M, HOMOGRAPHY_CORRELATION_HI) ** 2
        + U_SHAPE_LO_M**2
    )
    hi = math.sqrt(
        combined_position_uncertainty(U_COORD_HI_M, U_COORD_HI_M, HOMOGRAPHY_CORRELATION_LO) ** 2
        + U_SHAPE_HI_M**2
    )
    return round(lo, 3), round(hi, 3)

# IPCC AR6 calibrated likelihood language (Mastrandrea et al. 2010). Mapped from the
# Bayesian verdict probability, inserted deterministically (the model never picks the hedge).
_IPCC: list[tuple[float, str]] = [
    (0.99, "virtually certain"),
    (0.90, "very likely"),
    (0.66, "likely"),
    (0.33, "about as likely as not"),
    (0.10, "unlikely"),
    (0.0, "very unlikely"),
]


def normal_cdf(z: float) -> float:
    """Standard normal CDF via the error function (stdlib, no scipy)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# Internal alias for the band math below; calibration.py validates this exact function.
_phi = normal_cdf


def _verbal(p: float) -> str:
    for threshold, word in _IPCC:
        if p >= threshold:
            return word
    return "very unlikely"


# The honest three-band confidence schema: our coarse freeze-frame margin is one-to-two orders
# noisier than SAOT's ~5 cm tolerance, so a too-close call defers to the official decision.
_CONFIDENCE_BAND = {"clear": "clear", "tight": "marginal", "very tight": "too_close_to_call"}


@dataclass(frozen=True)
class MarginUncertainty:
    margin_meters: float
    sigma_meters: float
    band: Band  # "clear" | "tight" | "very tight"
    confidence_band: ConfidenceBand  # "clear" | "marginal" | "too_close_to_call"
    defer_to_official: bool  # too-close: VARSITY describes the official decision, no precise claim
    p_verdict: float  # P(the verdict is correct) = Phi(|M| / sigma)
    likelihood: str  # the IPCC verbal hedge for p_verdict
    counterfactual_meters: float  # how far the player would move to flip the call (= |M|)
    note: str  # a one-line, honest band explanation


def _note(band: str, sigma_m: float, likelihood: str) -> str:
    cm = round(sigma_m * 100)
    if band == "very tight":
        return (
            f"Within the ~{cm} cm of measurement noise. On the geometry alone this is "
            f"{likelihood}; this is what cricket calls an Umpire's Call, and VARSITY trusts "
            "the official's decision."
        )
    if band == "tight":
        return f"Supported, but close to the ~{cm} cm of measurement noise."
    return f"Clear of the ~{cm} cm of measurement noise."


def quantify(margin_meters: float, *, sigma_meters: float = SIGMA_MARGIN_M) -> MarginUncertainty:
    """Quantify the offside margin's uncertainty into the 'VARSITY's Call' band."""
    m = abs(margin_meters)
    if m > 2 * sigma_meters:
        band = "clear"
    elif m > sigma_meters:
        band = "tight"
    else:
        band = "very tight"
    p = _phi(m / sigma_meters) if sigma_meters > 0 else 1.0
    likelihood = _verbal(p)
    return MarginUncertainty(
        margin_meters=round(margin_meters, 2),
        sigma_meters=sigma_meters,
        band=band,
        confidence_band=_CONFIDENCE_BAND[band],
        defer_to_official=band == "very tight",
        p_verdict=round(p, 3),
        likelihood=likelihood,
        counterfactual_meters=round(m, 2),
        note=_note(band, sigma_meters, likelihood),
    )
