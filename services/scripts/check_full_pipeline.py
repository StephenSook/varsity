"""Live end-to-end check: geometry -> Granite-embeddings RAG -> Granite -> Guardian.

Runs the real pipeline on the WC2022 fixture with live watsonx clients. Requires
the Runtime associated to the project and creds in .env.

Run from repo root:  PYTHONPATH=services python services/scripts/check_full_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

from app.geometry import FreezeFramePlayer
from app.pipeline import explain_offside_decision

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


def main() -> int:
    fixture_path = Path(__file__).resolve().parents[1] / "tests/fixtures/wc2022_offside_frame.json"
    fixture = json.loads(fixture_path.read_text())
    frame = [FreezeFramePlayer(**p) for p in fixture["players"]]
    res = explain_offside_decision(frame)
    print(
        f"is_offside={res.is_offside} margin={res.margin_meters}m "
        f"law={res.law} ({res.law_title})"
    )
    print(f"guardian: safe={res.safe} cites_law={res.cites_law}")
    print(f"explanation:\n{res.explanation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
