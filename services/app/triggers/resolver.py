"""Resilient VAR-trigger resolution.

Try the live sources in order - Sportmonks (primary, has the transitional 'Goal
Under Review'), then API-Football (fallback, final outcomes only) - and fall back to
the cached replay buffer (the deterministic floor) so the demo always gets a VAR
sequence even with no network. The live path is a flourish, never load-bearing.
"""

from __future__ import annotations

from app.triggers.replay import ReplayBuffer, canned_buffer
from app.triggers.sportmonks import VarEvent


def resolve_live_var_events(
    *,
    sportmonks: object | None = None,
    apifootball: object | None = None,
    replay: ReplayBuffer | None = None,
) -> tuple[list[VarEvent], str]:
    """Return (events, source_label). First non-empty live source wins; else replay."""
    replay = replay if replay is not None else canned_buffer()
    for name, client in (("sportmonks", sportmonks), ("api-football", apifootball)):
        if client is None:
            continue
        try:
            events = client.live_var_events()
        except Exception:
            continue
        if events:
            return events, name
    return replay.events(), "replay-buffer"


def pick_transitional(events: list[VarEvent]) -> VarEvent | None:
    """The transitional 'under review' event if present, else the first event."""
    for e in events:
        if e.transitional:
            return e
    return events[0] if events else None


def reviewing_stage(event: VarEvent, source: str) -> dict:
    """Build the transitional 'reviewing' SSE stage dict from a VAR event."""
    return {
        "stage": "reviewing",
        "source": source,
        "type": event.type_name,
        "detail": event.detail,
        "minute": event.minute,
    }
