"""Halpern-Pearl actual-cause + Miller-contrastive opener for an offside decision.

Frames the RECEIVED decision contrastively - "offside, rather than onside" - and names the
decisive cause: the attacker's margin to the offside line. For a one-dimensional margin the
Halpern-Pearl actual cause is immediate: flipping the sign of the margin falsifies the verdict
with no contingency set needed (W = {}), so the margin is a but-for cause with a
Chockler-Halpern responsibility of 1. This searches over the RECEIVED geometry only; it never
re-derives the call from raw video and never opines on whether the call was correct (the
scope-drift firewall: explanation, not adjudication).

Honest scope: StatsBomb 360 gives one position per player (role booleans, no body-part
keypoints), so the decisive cause we can name is the MARGIN, not the body part. The
"torso vs trailing foot" contrastive in the literature needs keypoint data we do not have, and
we do not fabricate it.

Grounded in: Halpern & Pearl actual causation (modified definition, Halpern, IJCAI 2015 /
Actual Causality, MIT Press 2016); Miller, "Contrastive explanation: a structural-model
approach" (Knowledge Engineering Review 36:e14, 2021); Chockler & Halpern, "Responsibility and
Blame: A Structural-Model Approach" (JAIR 22:93-115, 2004).
"""

from __future__ import annotations


def contrastive(*, is_offside: bool, margin_meters: float, within_noise: bool = False) -> dict:
    """Build the contrastive 'why fact rather than foil' SSE stage from the received geometry."""
    fact = "offside" if is_offside else "onside"
    foil = "onside" if is_offside else "offside"
    margin_m = abs(margin_meters)
    relation = "beyond" if is_offside else "behind"
    direction = "further back" if is_offside else "further forward"

    opener = f"{fact.capitalize()}, rather than {foil}."
    cause = (
        f"The decisive factor was the attacker being {margin_m:.2f} m {relation} the "
        f"second-to-last defender when the ball was played; had they been {margin_m:.2f} m "
        f"{direction}, the call would have flipped to {foil}."
    )
    if within_noise:
        cause += (
            " That margin is within the measurement noise, so this is a knife-edge call - "
            "VARSITY trusts the official's finer tracking."
        )
    return {
        "stage": "causal",
        "fact": fact,
        "foil": foil,
        "decisive_cause": "the attacker's margin to the offside line",
        "margin_cm": round(margin_m * 100),
        "responsibility": 1.0,  # but-for cause; no contingency set needed (W = {})
        "contingency_set_size": 0,
        "within_noise": within_noise,
        "opener": opener,
        "narration": f"{opener} {cause}",
    }
