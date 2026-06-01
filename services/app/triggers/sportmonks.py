"""Sportmonks live VAR-trigger client (the primary live trigger).

Polls a fixture's events (or in-play fixtures) for VAR / offside review events.
Auth is sent in the Authorization header, never in the URL. The canned StatsBomb
path is the deterministic floor; this live trigger is the flourish, never
load-bearing for the demo.

Note: the exact Sportmonks VAR event schema should be confirmed against live data;
``parse_var_events`` is intentionally defensive (checks several fields).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

BASE = "https://api.sportmonks.com/v3/football"
VAR_SIGNALS = ("var", "goal under review", "goal disallowed", "goal cancelled", "offside")


@dataclass
class VarEvent:
    fixture_id: int
    minute: int | None
    type_name: str
    detail: str | None


def _blob(event: dict) -> str:
    name = ((event.get("type") or {}).get("name") or event.get("type_name") or "").lower()
    detail = (event.get("info") or event.get("addition") or event.get("result") or "").lower()
    return f"{name} {detail}"


def parse_var_events(fixture_id: int, events: list[dict]) -> list[VarEvent]:
    """Extract VAR / offside review events from a Sportmonks events list."""
    out: list[VarEvent] = []
    for e in events:
        if any(sig in _blob(e) for sig in VAR_SIGNALS):
            name = (e.get("type") or {}).get("name") or e.get("type_name") or "VAR"
            detail = e.get("info") or e.get("addition") or e.get("result")
            out.append(
                VarEvent(
                    fixture_id=fixture_id,
                    minute=e.get("minute"),
                    type_name=name,
                    detail=detail,
                )
            )
    return out


class SportmonksClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("SPORTMONKS_API_KEY", "")

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = httpx.get(
            f"{BASE}{path}",
            headers={"Authorization": self.token},
            params=params or {},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def fixture_var_events(self, fixture_id: int) -> list[VarEvent]:
        data = self._get(f"/fixtures/{fixture_id}", {"include": "events"})
        events = (data.get("data") or {}).get("events") or []
        return parse_var_events(fixture_id, events)

    def live_var_events(self) -> list[VarEvent]:
        """Poll in-play fixtures and return any VAR events across them."""
        data = self._get("/livescores/inplay", {"include": "events"})
        out: list[VarEvent] = []
        for fx in data.get("data") or []:
            out.extend(parse_var_events(fx.get("id", 0), fx.get("events") or []))
        return out
