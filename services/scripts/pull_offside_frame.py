"""Pull one confirmed offside freeze-frame from StatsBomb 360 open data (WC 2022).

Run once at build time (needs network + requirements-data.txt). Saves a normalized
fixture the offline test re-runs the geometry engine against, so the real-data
confirmation lives in CI without a network call.

Usage (from the repo root, with the venv active and PYTHONPATH=services):
    python services/scripts/pull_offside_frame.py
"""

from __future__ import annotations

import json
import os
import sys

from statsbombpy import sb

from app.geometry import FreezeFramePlayer, compute_offside

WORLD_CUP_2022 = (43, 106)  # competition_id, season_id
OUT = "services/tests/fixtures/wc2022_offside_frame.json"


def _players(rows: list[dict]) -> list[FreezeFramePlayer]:
    out = []
    for r in rows:
        loc = r.get("location")
        if isinstance(loc, (list, tuple)) and len(loc) == 2:
            x, y = float(loc[0]), float(loc[1])
        else:
            x, y = float(r["x"]), float(r["y"])
        out.append(
            FreezeFramePlayer(
                x=x,
                y=y,
                teammate=bool(r.get("teammate")),
                actor=bool(r.get("actor")),
                keeper=bool(r.get("keeper")),
            )
        )
    return out


def main() -> int:
    comp, season = WORLD_CUP_2022
    matches = sb.matches(competition_id=comp, season_id=season)
    match_ids = [int(m) for m in matches["match_id"]]
    print(f"WC2022 matches: {len(match_ids)}")

    for mid in match_ids:
        try:
            frames = sb.frames(match_id=mid, fmt="dict")  # flat list of per-player records
        except Exception:
            continue
        if not frames:
            continue
        ev = sb.events(match_id=mid)
        type_by_id = dict(zip(ev["id"], ev["type"])) if "id" in ev and "type" in ev else {}

        for rec in frames:
            rows = rec.get("freeze_frame") or []
            eid = rec.get("event_uuid")
            defenders = [r for r in rows if not r.get("teammate")]
            attackers = [r for r in rows if r.get("teammate")]
            if len(defenders) < 2 or not attackers:
                continue
            players = _players(rows)
            try:
                res = compute_offside(players)
            except ValueError:
                continue
            # A real freeze-frame where the most advanced attacker is genuinely in an
            # offside position (ahead of the second-to-last opponent).
            if res.is_offside and 0.1 <= res.margin_meters <= 6.0:
                event_type = str(type_by_id.get(eid, "unknown"))
                print(f"match={mid} event={eid} type={event_type}")
                print(f"  offside_line_x={res.offside_line_x} attacker_x={res.attacker_x}")
                print(f"  margin_meters={res.margin_meters} is_offside={res.is_offside}")
                fixture = {
                    "source": "StatsBomb 360 open data, FIFA World Cup 2022",
                    "match_id": mid,
                    "event_id": str(eid),
                    "event_type": event_type,
                    "players": [
                        {
                            "x": p.x,
                            "y": p.y,
                            "teammate": p.teammate,
                            "actor": p.actor,
                            "keeper": p.keeper,
                        }
                        for p in players
                    ],
                    "expected_is_offside": res.is_offside,
                    "expected_margin_meters": res.margin_meters,
                }
                os.makedirs(os.path.dirname(OUT), exist_ok=True)
                with open(OUT, "w") as f:
                    json.dump(fixture, f, indent=2)
                print(f"saved {OUT}")
                return 0
    print("no usable offside freeze-frame found")
    return 2


if __name__ == "__main__":
    sys.exit(main())
