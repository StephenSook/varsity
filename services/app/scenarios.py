"""Canned demo scenarios: REAL StatsBomb 360 freeze-frames whose verdicts are
COMPUTED by the geometry engine, never assigned.

Three frames from the same World Cup 2022 match (Canada vs Morocco) prove the engine
DECIDES rather than replays a fixed answer:

  - offside : the most advanced attacker is clearly beyond the second-to-last opponent
  - onside  : the attacker is clearly behind the line
  - tight   : a razor-thin call within a few centimetres of the line (the VAR moment)

Pressing the selector re-streams a different real frame; the verdict word, the SVG
offside line, the verdict earcon and the haptic all flip on their own from the geometry.
Provenance / reproducible extraction: services/scripts/pull_scenarios.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.geometry import FreezeFramePlayer

_FIXTURES = Path(__file__).resolve().parent.parent / "tests/fixtures"
_FILES = {
    "offside": "wc2022_offside_frame.json",
    "onside": "wc2022_onside_frame.json",
    "tight": "wc2022_tight_frame.json",
}
_LABELS = {"offside": "Clear offside", "onside": "Clear onside", "tight": "Razor-tight"}
DEFAULT_SCENARIO = "offside"


def scenario_names() -> list[str]:
    return list(_FILES)


def _resolve(name: str) -> str:
    return name if name in _FILES else DEFAULT_SCENARIO


def _data(name: str) -> dict:
    return json.loads((_FIXTURES / _FILES[_resolve(name)]).read_text())


def load_frame(name: str) -> list[FreezeFramePlayer]:
    return [FreezeFramePlayer(**p) for p in _data(name)["players"]]


def trigger_meta(name: str) -> dict:
    """The trigger-stage payload: the World Cup byline for this scenario."""
    name = _resolve(name)
    d = _data(name)
    year = (d.get("match_date") or "")[:4]
    return {
        "source": "StatsBomb 360 (canned)",
        "scenario": name,
        "label": _LABELS.get(name, name),
        "competition": "FIFA World Cup 2022",
        "match_name": d.get("match_name"),
        "year": int(year) if year.isdigit() else None,
        "minute": d.get("minute"),
        "passer": d.get("player"),  # the player who played the ball (360 positions are anonymous)
        "expected_is_offside": d.get("expected_is_offside"),
        "expected_margin_meters": d.get("expected_margin_meters"),
    }


def scenarios_index() -> list[dict]:
    """All scenarios with their bylines, for the selector and the /judges panel."""
    return [trigger_meta(n) for n in _FILES]
