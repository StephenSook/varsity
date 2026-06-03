"""Pull the VARSITY scenario set from StatsBomb 360 open data (FIFA World Cup 2022).

Build-time provenance (needs network + requirements-data.txt OR just urllib over the
open-data raw JSON, as used here). Produces three REAL freeze-frame fixtures from the
same match so the demo can prove the geometry DECIDES the verdict (not a hardcode):

  - wc2022_offside_frame.json  a clear offside (the most advanced attacker well beyond
                               the second-to-last opponent)  -> enriched with match meta
  - wc2022_onside_frame.json   a clear onside (the attacker behind the line)
  - wc2022_tight_frame.json    a razor-tight call (|margin| within a few cm of the line)

Every verdict (offside / onside) and margin is COMPUTED by app.geometry.compute_offside
from the real positional data; nothing is assigned. The fixtures carry match/minute/
player metadata for the on-screen "World Cup moment" byline.

Usage (repo root):  PYTHONPATH=services .venv/bin/python services/scripts/pull_scenarios.py
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from app.geometry import FreezeFramePlayer, compute_offside

MATCH_ID = 3857276  # Canada vs Morocco, FIFA World Cup 2022 (group stage)
COMP, SEASON = 43, 106
BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
FIXTURES = Path(__file__).resolve().parent.parent / "tests/fixtures"
OFFSIDE_EVENT = "1f1b0ef8-1a1d-45b3-bf9c-4299ea836377"  # the existing 5.45m offside frame


def _get(url: str):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def _players(rows: list[dict]) -> list[FreezeFramePlayer]:
    out = []
    for r in rows:
        loc = r.get("location")
        if isinstance(loc, (list, tuple)) and len(loc) == 2:
            out.append(
                FreezeFramePlayer(
                    x=float(loc[0]),
                    y=float(loc[1]),
                    teammate=bool(r.get("teammate")),
                    actor=bool(r.get("actor")),
                    keeper=bool(r.get("keeper")),
                )
            )
    return out


def _dump(players: list[FreezeFramePlayer], res, meta: dict, path: Path) -> None:
    fixture = {
        **meta,
        "players": [
            {"x": p.x, "y": p.y, "teammate": p.teammate, "actor": p.actor, "keeper": p.keeper}
            for p in players
        ],
        "expected_is_offside": res.is_offside,
        "expected_margin_meters": res.margin_meters,
    }
    path.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"saved {path.name}: is_offside={res.is_offside} margin={res.margin_meters}m")


def main() -> int:
    matches = _get(f"{BASE}/matches/{COMP}/{SEASON}.json")
    m = next(x for x in matches if x["match_id"] == MATCH_ID)
    match_name = f"{m['home_team']['home_team_name']} vs {m['away_team']['away_team_name']}"
    match_date = m.get("match_date")
    stage = m.get("competition_stage", {}).get("name")
    print(f"MATCH {MATCH_ID}: {match_name} ({match_date}, {stage})")

    threesixty = _get(f"{BASE}/three-sixty/{MATCH_ID}.json")
    events = _get(f"{BASE}/events/{MATCH_ID}.json")
    emeta = {
        e["id"]: (e.get("minute"), (e.get("player") or {}).get("name"), (e.get("type") or {}).get("name"))
        for e in events
    }

    base_meta = {
        "source": "StatsBomb 360 open data, FIFA World Cup 2022",
        "match_id": MATCH_ID,
        "match_name": match_name,
        "match_date": match_date,
        "competition_stage": stage,
    }

    # Index frames by event, compute the verdict for each, keep clean Pass frames.
    recs = []
    for rec in threesixty:
        eid = rec.get("event_uuid")
        players = _players(rec.get("freeze_frame") or [])
        defs = [p for p in players if not p.teammate]
        atts = [p for p in players if p.teammate]
        if len(defs) < 2 or not atts or len(players) < 12:
            continue
        try:
            res = compute_offside(players)
        except ValueError:
            continue
        minute, player, etype = emeta.get(eid, (None, None, None))
        recs.append((eid, players, res, minute, player, etype))

    # ONSIDE: a clear Pass where the attacker is comfortably behind the line.
    onside = sorted(
        [r for r in recs if (not r[2].is_offside) and -5.0 <= r[2].margin_meters <= -1.5 and r[5] == "Pass"],
        key=lambda r: (abs(r[2].margin_meters + 3.0), -len(r[1])),  # prefer ~3m behind, fuller frames
    )
    # TIGHT: the razor-thin VAR call (smallest absolute margin), Pass frame.
    tight = sorted(
        [r for r in recs if abs(r[2].margin_meters) <= 0.2 and r[5] == "Pass"],
        key=lambda r: (abs(r[2].margin_meters), -len(r[1])),
    )

    # OFFSIDE: enrich the existing 5.45m fixture in place (keep players + expected).
    off_path = FIXTURES / "wc2022_offside_frame.json"
    off = json.loads(off_path.read_text())
    o_min, o_player, o_type = emeta.get(OFFSIDE_EVENT, (None, None, None))
    off.update(
        {
            "match_name": match_name,
            "match_date": match_date,
            "competition_stage": stage,
            "minute": o_min,
            "player": o_player,
            "event_type": off.get("event_type", o_type),
            "scenario": "offside",
        }
    )
    off_path.write_text(json.dumps(off, indent=2) + "\n")
    print(f"enriched offside: {match_name} min {o_min} {o_player} -> {off['expected_margin_meters']}m offside")

    if not onside or not tight:
        print("WARN: missing onside or tight candidate")
        return 2

    e_on, p_on, r_on, min_on, pl_on, _ = onside[0]
    _dump(p_on, r_on, {**base_meta, "event_id": e_on, "event_type": "Pass", "minute": min_on, "player": pl_on, "scenario": "onside"}, FIXTURES / "wc2022_onside_frame.json")
    print(f"  onside: min {min_on} {pl_on}")

    e_t, p_t, r_t, min_t, pl_t, _ = tight[0]
    _dump(p_t, r_t, {**base_meta, "event_id": e_t, "event_type": "Pass", "minute": min_t, "player": pl_t, "scenario": "tight"}, FIXTURES / "wc2022_tight_frame.json")
    print(f"  tight: min {min_t} {pl_t} (off={r_t.is_offside})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
