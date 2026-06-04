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

# --- The HONEST broadcast-annotation budget: what VARSITY actually consumes. DOCUMENTED Type-B
#     estimates, NOT a published StatsBomb spec. The differential margin is much tighter than the
#     absolute coordinate because the same-frame homography error cancels (correlation r). gum.py
#     imports these primitives, so the band and the GUM budget share ONE source (no drift). ---
U_COORD_BROADCAST_M = 0.60  # per-coordinate Type-B std for a broadcast-annotated point (absolute)
HOMOGRAPHY_CORRELATION = 0.70  # r: same-frame homography systematic error cancels in the difference
U_SHAPE_M = 0.30  # body-anchor: Law 11 furthest-forward part vs the annotated point
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
    band: str  # "clear" | "tight" | "very tight"
    confidence_band: str  # "clear" | "marginal" | "too_close_to_call" (the honest schema)
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
