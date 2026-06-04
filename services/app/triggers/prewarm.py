"""Speculative pre-warm of the explanation pipeline.

A VAR review has a gap: the officials signal 'under review', then 15-45s later the
outcome. We use that gap. On ``review_started`` we pre-compute the OUTCOME-INDEPENDENT
work - retrieve the Law and run the freeze-frame geometry - and cache it keyed by the
review. When the official outcome lands we reuse the cached facts, so the trigger ->
spoken-verdict path skips the cold retrieval + geometry and emits in a fraction of the
cold-start time.

Honesty: pre-warm caches FACTS (the rule text and the geometry of the frozen moment),
never a verdict. Both outcome branches (goal disallowed / goal confirmed) are prepared
from those facts; the official's RECEIVED decision selects which one is spoken. We never
predict the call - we prepare to explain whichever call arrives.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.geometry import FreezeFramePlayer, compute_offside

# The outcome-independent Law query warmed during the review gap.
_PREWARM_QUERY = "offside attacker nearer the goal line than the second-last opponent and the ball"


def branch_key(outcome: str | None) -> str:
    """Map the official's received outcome to a prepared branch (never a prediction)."""
    low = (outcome or "").lower()
    if "disallow" in low or "cancel" in low or "offside" in low:
        return "goal_disallowed"
    return "goal_confirmed"


@dataclass(frozen=True)
class WarmedReview:
    review_id: str
    law: Any  # the retrieved LawChunk (outcome-independent)
    geometry: Any  # the OffsideResult for the frame
    branches: dict[str, dict]  # prepared facts per outcome
    warmed_at: float

    def select(self, outcome: str | None) -> dict:
        """Pick the prepared branch matching the official's received outcome."""
        return self.branches.get(branch_key(outcome), self.branches["goal_disallowed"])


class PreWarmCache:
    """Holds warmed reviews keyed by review id. ``consume`` pops (a review resolves once)."""

    def __init__(self) -> None:
        self._warm: dict[str, WarmedReview] = {}

    def warm(
        self,
        review_id: str,
        frame: list[FreezeFramePlayer],
        retriever: Any,
        *,
        ball_x: float | None = None,
        query: str = _PREWARM_QUERY,
    ) -> WarmedReview:
        """Do the slow, outcome-independent work NOW (during the review gap): retrieve the
        Law and run the geometry, prepare both outcome branches, and cache the result.
        """
        law = retriever.retrieve(query)
        geom = compute_offside(frame, ball_x=ball_x)
        margin = abs(geom.margin_meters)
        branches = {
            "goal_disallowed": {"verdict": "offside", "margin_meters": margin, "law": law.law},
            "goal_confirmed": {"verdict": "onside", "margin_meters": margin, "law": law.law},
        }
        warmed = WarmedReview(
            review_id=review_id,
            law=law,
            geometry=geom,
            branches=branches,
            warmed_at=time.monotonic(),
        )
        self._warm[review_id] = warmed
        return warmed

    def consume(self, review_id: str) -> WarmedReview | None:
        """Pop the warmed facts when the outcome lands. None on a miss (warm a cold path)."""
        return self._warm.pop(review_id, None)

    def warmed(self, review_id: str) -> bool:
        return review_id in self._warm
