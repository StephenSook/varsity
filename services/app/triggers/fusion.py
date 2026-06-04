"""Multi-source fusion confidence for VAR triggers.

Two feeds (Sportmonks primary, API-Football fallback) can each report the same VAR
review. When they AGREE we are more confident; when only one has fired we hedge; when
they CONFLICT we surface the conflict and stay unconfirmed. This raises confidence and
resilience - it NEVER adjudicates: we never invent or pick an outcome. On conflict we
report no outcome and lower the confidence so the narrator hedges, pairing with the
Wave-A uncertainty band rather than guessing.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from app.triggers.schema import REVIEW_STARTED, VARDecisionEvent

# Base confidence per phase, before the multi-source agreement bonus.
_BASE = {REVIEW_STARTED: 0.70}
_BASE_RESOLVED = 0.85
# Each agreeing source beyond the first adds this, capped so we never claim certainty.
_AGREE_BONUS = 0.06
_MAX_CONFIDENCE = 0.97
# A genuine cross-source conflict on the outcome.
_CONFLICT_CONFIDENCE = 0.50


@dataclass(frozen=True)
class FusedDecision:
    fixture_id: int
    minute: int | None
    phase: str
    review_reason: str | None
    outcome: str | None
    confidence: float
    sources: tuple[str, ...]
    outcomes: tuple[str, ...]  # the distinct normalized outcomes the sources reported
    conflict: bool
    hedge: str

    def as_dict(self) -> dict:
        return {
            "fixture_id": self.fixture_id,
            "minute": self.minute,
            "phase": self.phase,
            "review_reason": self.review_reason,
            "outcome": self.outcome,
            "confidence": round(self.confidence, 3),
            "sources": list(self.sources),
            "conflict": self.conflict,
            "hedge": self.hedge,
        }


def _norm_outcome(outcome: str | None) -> str | None:
    """Collapse a feed's outcome wording onto a coarse class so two feeds that phrase the
    same call differently still count as AGREEING (and genuinely-different calls conflict).
    """
    if outcome is None:
        return None
    low = outcome.lower()
    if "disallow" in low or "cancel" in low or "offside" in low:
        return "goal_disallowed"
    if "no penalty" in low:
        return "no_penalty"
    if "penalty" in low:
        return "penalty"
    if "goal" in low or "confirm" in low or "allow" in low:
        return "goal_confirmed"
    return low.strip()


def _hedge(phase: str, conflict: bool, sources: tuple[str, ...]) -> str:
    if conflict:
        return "Feeds disagree on this call; treating it as unconfirmed and awaiting confirmation."
    if phase == REVIEW_STARTED:
        return "A VAR review appears to be underway."
    if len(sources) > 1:
        return f"Confirmed by multiple feeds ({', '.join(sources)})."
    return f"Confirmed by {sources[0]}."


def fuse(events: Iterable[VARDecisionEvent]) -> list[FusedDecision]:
    """Group events by (fixture, minute, phase) across sources and fuse a confidence.

    The correlation key is coarse on purpose: a review at a fixture/minute is one event
    even when two feeds label it slightly differently. Resilient over-merging beats
    splitting one real review into two low-confidence ghosts.
    """
    groups: dict[tuple, list[VARDecisionEvent]] = defaultdict(list)
    for e in events:
        groups[(e.fixture_id, e.minute, e.phase)].append(e)

    fused: list[FusedDecision] = []
    for (fixture_id, minute, phase), group in groups.items():
        sources = tuple(dict.fromkeys(e.source for e in group))  # de-dup, keep order
        outcomes = tuple(
            dict.fromkeys(_norm_outcome(e.outcome) for e in group if e.outcome is not None)
        )
        conflict = len(outcomes) > 1
        if conflict:
            confidence = _CONFLICT_CONFIDENCE
            outcome = None  # never pick a side
        else:
            bonus = _AGREE_BONUS * max(0, len(sources) - 1)
            base = _BASE.get(phase, _BASE_RESOLVED)
            confidence = min(_MAX_CONFIDENCE, base + bonus)
            outcome = next((e.outcome for e in group if e.outcome is not None), None)
        # The replay/canned floor is deterministic; never downgrade it below full confidence.
        if sources == ("replay-buffer",):
            confidence = 1.0
        confidence = round(confidence, 3)  # avoid binary-float noise (0.85 + 0.06)
        reason = next((e.review_reason for e in group if e.review_reason), None)
        fused.append(
            FusedDecision(
                fixture_id=fixture_id,
                minute=minute,
                phase=phase,
                review_reason=reason,
                outcome=outcome,
                confidence=confidence,
                sources=sources,
                outcomes=outcomes,
                conflict=conflict,
                hedge=_hedge(phase, conflict, sources),
            )
        )
    return fused
