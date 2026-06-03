"""Uncertainty quantification for the offside margin - the "VARSITY's Call" band.

The received margin is an estimate: the freeze-frame coordinates carry measurement error.
Propagating that error gives an honest band on the margin, a Bayesian confidence in the
verdict, a calibrated verbal likelihood, and a contrastive counterfactual. VARSITY
DESCRIBES the received decision's sensitivity to measurement noise; it never adjudicates.

Per-player optical-tracking position RMSE is ~9 cm (Linke, Link & Lames, "Football-specific
validity of TRACAB's optical video tracking systems", PLOS ONE 2020, 15(3):e0230179 -
Gen4 0.09 m / Gen5 0.08 m; corroborated by Blauberger et al., Sensors 2021, 9 cm/player).
StatsBomb 360 gives a single (x, y) per player (not a skeleton), so the propagated 1-sigma
on the margin is sigma_M = sqrt(sigma_A^2 + sigma_D^2) ~= 13 cm - wider than the Premier
League's ~5 cm "thicker-lines" tolerance, which is the honest, fan-shocking finding.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Per-player position RMSE (m), conservative Gen4 figure from Linke et al. 2020.
PLAYER_RMSE_M = 0.09
# Propagated 1-sigma on the margin M = X_A - X_D for independent per-player errors.
SIGMA_MARGIN_M = round(math.sqrt(2.0) * PLAYER_RMSE_M, 3)  # ~= 0.127 m

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


def _phi(z: float) -> float:
    """Standard normal CDF via the error function (stdlib, no scipy)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _verbal(p: float) -> str:
    for threshold, word in _IPCC:
        if p >= threshold:
            return word
    return "very unlikely"


@dataclass(frozen=True)
class MarginUncertainty:
    margin_meters: float
    sigma_meters: float
    band: str  # "clear" | "tight" | "very tight"
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
        p_verdict=round(p, 3),
        likelihood=likelihood,
        counterfactual_meters=round(m, 2),
        note=_note(band, sigma_meters, likelihood),
    )
