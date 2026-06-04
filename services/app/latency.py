"""Honest end-to-end latency framing for the 'first in the room' thesis.

VARSITY's claim is that a blind fan hears the WHY before the broadcast picture even
catches up to the on-field moment. This module holds the VERIFIED broadcast-delay
figures (so the claim is calibrated, not the false '4-8s'), a trigger -> spoken-verdict
budget, and the honest framing per delivery path.

Sources (primary): Phenix 'Field of Play' Super Bowl latency studies - over-the-air
(OTA) broadcast ~18s (2023) and ~22s (2024) behind the field of play; cable ~28-50s;
OTT / streaming ~30-60s+ (FOX Sports app ~24s best case, several others 50-80s). Reported
via Sports Video Group, 2024-02-12.

HONESTY CAVEAT: Phenix is a low-latency-streaming vendor (a commercial interest in large
delay figures), and the measurement is field-of-play (the whole camera-to-air production
chain), not pure encoder-to-display transmission (~5-12s). The field-of-play framing is
the right one here: the blind fan is racing the actual on-field event, not the encoder.
"""

from __future__ import annotations

from dataclasses import dataclass

# Trigger -> spoken-verdict budget. At or below this, VARSITY beats every delivery path.
LATENCY_BUDGET_S = 10.0

# Verified broadcast delay behind the field of play, per delivery path (seconds).
# Conservative single figures taken from the low end of the Phenix studies.
BROADCAST_DELAY_S: dict[str, float] = {
    "ota": 18.0,  # over-the-air (the toughest path to beat; Phenix 2023)
    "cable": 28.0,  # cable (Phenix 2023; up to ~50s in 2024)
    "streaming": 35.0,  # OTT / HLS-DASH typical (commonly 30-60s, worse for live sports)
}
# The path we headline against (OTA, the hardest to beat).
DEFAULT_PATH = "ota"

SOURCES = (
    "Phenix Field-of-Play Super Bowl studies (OTA ~18s 2023 / ~22s 2024, cable ~28-50s, "
    "streaming ~30-60s+), via Sports Video Group 2024-02-12"
)
CAVEAT = (
    "Phenix is a low-latency vendor and measures field-of-play (the full production "
    "chain), not pure transmission (~5-12s); the field-of-play framing is the honest one "
    "for a fan racing the live event."
)
NOTE = "The live trigger is never load-bearing; the canned StatsBomb path is the floor."


@dataclass(frozen=True)
class LatencyReport:
    elapsed_s: float
    within_budget: bool
    leads_s: dict[str, float]  # seconds ahead of each delivery path (>= 0)
    headline: str


def lead_over(elapsed_s: float, path: str = DEFAULT_PATH) -> float:
    """Seconds VARSITY is ahead of the given delivery path's picture (never negative)."""
    return max(0.0, BROADCAST_DELAY_S.get(path, BROADCAST_DELAY_S[DEFAULT_PATH]) - elapsed_s)


def report(elapsed_s: float) -> LatencyReport:
    leads = {path: round(lead_over(elapsed_s, path), 1) for path in BROADCAST_DELAY_S}
    ota = leads[DEFAULT_PATH]
    headline = (
        f"Explained {ota:.1f}s before the over-the-air broadcast picture."
        if ota >= 1.0
        else "Explained in step with the broadcast picture."
    )
    return LatencyReport(
        elapsed_s=round(elapsed_s, 2),
        within_budget=elapsed_s <= LATENCY_BUDGET_S,
        leads_s=leads,
        headline=headline,
    )


def payload(elapsed_s: float | None = None) -> dict:
    """The /latency framing: the verified delays, the budget, the honesty caveat, and
    (when ``elapsed_s`` is given) the calibrated lead for a specific run."""
    out: dict = {
        "budget_s": LATENCY_BUDGET_S,
        "broadcast_delay_s": BROADCAST_DELAY_S,
        "default_path": DEFAULT_PATH,
        "sources": SOURCES,
        "caveat": CAVEAT,
        "note": NOTE,
    }
    if elapsed_s is not None:
        r = report(elapsed_s)
        out["run"] = {
            "elapsed_s": r.elapsed_s,
            "within_budget": r.within_budget,
            "leads_s": r.leads_s,
            "headline": r.headline,
        }
    return out
