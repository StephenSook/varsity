"""Normalized VAR decision event schema + feed-adapter port.

Hexagonal ports-and-adapters: every live source (Sportmonks, API-Football, the replay
buffer, StatsBomb 360) is an ADAPTER that emits the same ``VARDecisionEvent``, so the
explainer depends only on this schema, never on a source's raw payload. The schema is
the seam the multi-source fusion (``fusion.py``) and the speculative pre-warm
(``prewarm.py``) build on.

In concept: this carries a RECEIVED decision (what the officials signalled) to the
explainer. It never predicts or adjudicates. ``outcome`` is null while a review is in
progress and is only ever the official's signalled result, never a guess.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.triggers.sportmonks import VarEvent

# The two phases of a VAR review. review_started carries no outcome (the officials are
# still deciding); review_resolved carries the official's signalled result.
REVIEW_STARTED = "review_started"
REVIEW_RESOLVED = "review_resolved"

# Coarse reasons we can read off a feed blob. Used only to LABEL the review, never to
# decide it - the geometry/Law layer does the explaining.
_REASON_KEYS = (
    ("offside", "Offside"),
    ("hand ball", "Handball"),
    ("handball", "Handball"),
    ("penalty", "Penalty"),
    ("foul", "Foul"),
)


def _reason_of(blob: str) -> str | None:
    low = blob.lower()
    for needle, label in _REASON_KEYS:
        if needle in low:
            return label
    return None


@dataclass(frozen=True)
class VARDecisionEvent:
    """One normalized VAR decision, source-agnostic.

    ``event_id`` is adapter-prefixed (``"sportmonks:998:10"``) so events from different
    feeds never collide and dedup is exact. ``confidence`` is filled by the fusion layer
    (1.0 for the deterministic replay floor); ``geometry_ref`` names the freeze-frame
    that backs the explanation, if any.
    """

    event_id: str
    source: str
    phase: str
    fixture_id: int
    minute: int | None
    review_reason: str | None
    outcome: str | None
    confidence: float = 1.0
    sort_order: int | None = None
    geometry_ref: str | None = None
    raw: dict = field(default_factory=dict)

    @property
    def transitional(self) -> bool:
        return self.phase == REVIEW_STARTED

    def as_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "phase": self.phase,
            "fixture_id": self.fixture_id,
            "minute": self.minute,
            "review_reason": self.review_reason,
            "outcome": self.outcome,
            "confidence": round(self.confidence, 3),
            "sort_order": self.sort_order,
            "geometry_ref": self.geometry_ref,
        }


@runtime_checkable
class FeedAdapter(Protocol):
    """A live-feed port: any source that yields normalized VAR decision events.

    The explainer and the resolver depend on this Protocol, not on a concrete client, so
    a new feed is just a new adapter - the explanation path never changes.
    """

    name: str

    def fetch(self) -> list[VARDecisionEvent]: ...


def normalize(
    event: VarEvent, source: str, *, geometry_ref: str | None = None
) -> VARDecisionEvent:
    """Map a source ``VarEvent`` onto the normalized schema.

    The phase is read from the event itself (the transitional 'Goal Under Review' is
    review_started; everything else is the resolved outcome). ``outcome`` is withheld
    while the review is in progress - we never fill it with a prediction.
    """
    started = event.transitional
    blob = f"{event.type_name} {event.detail or ''}"
    # Adapter-prefixed id; fall back to (minute, type) when the feed gives no integer id
    # so dedup still works on the replay/canned path.
    raw_id = event.event_id if event.event_id is not None else f"{event.minute}:{event.type_name}"
    return VARDecisionEvent(
        event_id=f"{source}:{event.fixture_id}:{raw_id}",
        source=source,
        phase=REVIEW_STARTED if started else REVIEW_RESOLVED,
        fixture_id=event.fixture_id,
        minute=event.minute,
        review_reason=_reason_of(blob),
        outcome=None if started else event.detail,
        sort_order=event.sort_order,
        geometry_ref=geometry_ref,
        raw={"type_name": event.type_name, "detail": event.detail},
    )


def normalize_all(
    events: Iterable[VarEvent], source: str, *, geometry_ref: str | None = None
) -> list[VARDecisionEvent]:
    return [normalize(e, source, geometry_ref=geometry_ref) for e in events]


def dedup_and_sort(events: Iterable[VARDecisionEvent]) -> list[VARDecisionEvent]:
    """Dedup on ``event_id`` (a feed repeats an event across polls) and order by
    ``sort_order`` then ``minute``.

    NEVER order by minute alone: Sportmonks events carry no per-event timestamp and
    several can share a minute, so ``sort_order`` (the feed's own order) is the key.
    Events with no sort_order sort last, in minute order.
    """
    seen: set[str] = set()
    unique: list[VARDecisionEvent] = []
    for e in events:
        if e.event_id in seen:
            continue
        seen.add(e.event_id)
        unique.append(e)
    return sorted(
        unique, key=lambda e: (e.sort_order is None, e.sort_order or 0, e.minute or 0)
    )
