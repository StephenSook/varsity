"""Cached replay buffer for the live-trigger beat.

Live VAR in the demo window is <1% likely, so the demo replays a recorded sequence -
the transitional 'Goal Under Review' then the final 'Goal disallowed - offside' - as
a deterministic floor that never depends on a live API. The canned StatsBomb pipeline
remains the explanation floor.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from app.triggers.sportmonks import VarEvent

# A recorded WC-style offside review: transitional announcement, then the verdict.
CANNED_REVIEW: tuple[VarEvent, ...] = (
    VarEvent(
        fixture_id=0,
        minute=23,
        type_name="Goal Under Review",
        detail="VAR is reviewing a possible goal",
    ),
    VarEvent(
        fixture_id=0,
        minute=23,
        type_name="Goal Disallowed",
        detail="Goal disallowed - offside",
    ),
)


class ReplayBuffer:
    """Holds recent (or canned) VAR events and replays them in order."""

    def __init__(self, events: Iterable[VarEvent] | None = None, maxlen: int = 20) -> None:
        self._buf: deque[VarEvent] = deque(events or (), maxlen=maxlen)

    def record(self, events: Iterable[VarEvent]) -> None:
        self._buf.extend(events)

    def events(self) -> list[VarEvent]:
        return list(self._buf)

    def empty(self) -> bool:
        return not self._buf


def canned_buffer() -> ReplayBuffer:
    """The deterministic replay floor: a recorded offside review sequence."""
    return ReplayBuffer(CANNED_REVIEW)
