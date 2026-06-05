"""API-Football fallback VAR-trigger client.

API-Football emits FINAL VAR outcomes only (no transitional 'review in progress'
state) via /fixtures/events: type 'Var', detail e.g. 'Goal Disallowed - offside'.
Sportmonks stays primary because only it has the transitional 'Goal Under Review'.
Auth via the x-apisports-key header, never the URL.
"""

from __future__ import annotations

import os

import httpx

from app.triggers.sportmonks import VarEvent

BASE = "https://v3.football.api-sports.io"


def parse_api_football_events(fixture_id: int, events: list[dict]) -> list[VarEvent]:
    """Extract VAR events (type 'Var') from an API-Football events list."""
    out: list[VarEvent] = []
    for e in events:
        if str(e.get("type", "")).lower() == "var":
            out.append(
                VarEvent(
                    fixture_id=fixture_id,
                    minute=(e.get("time") or {}).get("elapsed"),
                    type_name="Var",
                    detail=e.get("detail"),
                )
            )
    return out


class ApiFootballClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("API_FOOTBALL_KEY", "")

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = httpx.get(
            f"{BASE}{path}",
            headers={"x-apisports-key": self.token},
            params=params or {},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def fixture_var_events(self, fixture_id: int) -> list[VarEvent]:
        data = self._get("/fixtures/events", {"fixture": fixture_id})
        return parse_api_football_events(fixture_id, data.get("response") or [])

    def live_var_events(self) -> list[VarEvent]:
        """Poll live fixtures and return any VAR events across them."""
        data = self._get("/fixtures", {"live": "all"})
        out: list[VarEvent] = []
        for fx in data.get("response") or []:
            fid = (fx.get("fixture") or {}).get("id", 0)
            out.extend(parse_api_football_events(fid, fx.get("events") or []))
        return out

    def live_fixtures(self) -> list[dict]:
        """The matches live right now (league, teams, minute) + any VAR event detail per match,
        for the judge-facing 'what is live now' proof. One on-demand call; the route caches it."""
        data = self._get("/fixtures", {"live": "all"})
        out: list[dict] = []
        for fx in data.get("response") or []:
            fixture = fx.get("fixture") or {}
            teams = fx.get("teams") or {}
            var = parse_api_football_events(fixture.get("id", 0), fx.get("events") or [])
            out.append(
                {
                    "league": (fx.get("league") or {}).get("name"),
                    "home": (teams.get("home") or {}).get("name"),
                    "away": (teams.get("away") or {}).get("name"),
                    "minute": (fixture.get("status") or {}).get("elapsed"),
                    "var_events": [v.detail for v in var if v.detail],
                }
            )
        return out
