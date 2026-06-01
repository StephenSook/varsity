import json
import pathlib

from app.geometry import FreezeFramePlayer, compute_offside

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "wc2022_offside_frame.json"


def test_real_wc2022_offside_frame_reproduces_margin() -> None:
    """The geometry engine reproduces the offside margin on a real StatsBomb 360 frame.

    The fixture was pulled once from StatsBomb World Cup 2022 open data via
    services/scripts/pull_offside_frame.py. This runs offline in CI.
    """
    data = json.loads(FIXTURE.read_text())
    frame = [FreezeFramePlayer(**p) for p in data["players"]]
    res = compute_offside(frame)
    assert res.is_offside == data["expected_is_offside"]
    assert abs(res.margin_meters - data["expected_margin_meters"]) < 0.01
    # A real attacker-in-offside-position frame: positive margin ahead of the line.
    assert res.is_offside is True
    assert res.margin_meters > 0
