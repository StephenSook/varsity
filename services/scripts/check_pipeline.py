"""End-to-end sacred-core smoke test: geometry -> Granite -> Law-grounded explanation.

Loads the real StatsBomb WC2022 offside fixture, computes the offside margin, then
asks live watsonx Granite to explain it grounded in Law 11. Tries both Granite
models so we can pick the best one for GRANITE_MODEL_ID. Run after the watsonx.ai
Runtime is associated to the project.

Run from repo root:  PYTHONPATH=services python services/scripts/check_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

from app.geometry import FreezeFramePlayer, compute_offside
from app.llm.granite import GraniteClient, GraniteConfig

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

LAW11 = (
    "Law 11 - Offside. A player is in an offside position if any part of the head, body "
    "or feet is in the opponents' half (excluding the halfway line) and nearer to the "
    "opponents' goal line than both the ball and the second-last opponent when the ball "
    "is played by a team-mate. Being in an offside position is only an offence if the "
    "player becomes involved in active play. The hands and arms are not considered."
)

MODELS = ["ibm/granite-3-8b-instruct", "ibm/granite-4-h-small"]


def main() -> int:
    fixture_path = Path(__file__).resolve().parents[1] / "tests/fixtures/wc2022_offside_frame.json"
    fixture = json.loads(fixture_path.read_text())
    frame = [FreezeFramePlayer(**p) for p in fixture["players"]]
    res = compute_offside(frame)
    print(f"geometry: is_offside={res.is_offside} margin={res.margin_meters}m")

    for model in MODELS:
        cfg = GraniteConfig.from_env()
        cfg.model_id = model
        client = GraniteClient(cfg)
        try:
            out = client.explain_offside(
                margin_meters=res.margin_meters,
                is_offside=res.is_offside,
                law_text=LAW11,
            )
            print(f"\n[{model}]\n{out}")
        except Exception as exc:
            print(f"\n[{model}] ERROR {type(exc).__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
