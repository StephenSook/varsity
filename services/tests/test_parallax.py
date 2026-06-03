import math

from app import parallax
from app.geometry import FreezeFramePlayer


def _frame(attacker_y, defender_y):
    return [
        FreezeFramePlayer(x=100.0, y=attacker_y, teammate=True),
        FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=98.0, y=defender_y, teammate=False),
        FreezeFramePlayer(x=119.0, y=40.0, teammate=False, keeper=True),
    ]


def test_lateral_separation_in_metres() -> None:
    # 20 StatsBomb y-units apart -> 20 * 68/80 = 17.0 m
    out = parallax.estimate(_frame(30.0, 50.0))
    assert out["lateral_separation_m"] == 17.0


def test_apparent_shift_uses_camera_angle() -> None:
    out = parallax.estimate(_frame(30.0, 50.0))
    expected = round(17.0 * math.tan(math.radians(30.0)) * 100)
    assert out["apparent_shift_cm"] == expected
    assert out["camera_angle_deg"] == 30.0


def test_zero_lateral_separation_is_no_parallax() -> None:
    out = parallax.estimate(_frame(40.0, 40.0))
    assert out["lateral_separation_m"] == 0.0
    assert out["apparent_shift_cm"] == 0


def test_note_is_screen_reader_prose_without_adjudicating() -> None:
    note = parallax.estimate(_frame(30.0, 50.0))["note"].lower()
    assert "camera" in note
    assert "real positions" in note
    # never re-adjudicates: no verdict words in the parallax narration
    assert "offside" not in note and "onside" not in note


def test_stage_shape() -> None:
    s = parallax.parallax_stage(_frame(30.0, 50.0))
    assert s["stage"] == "parallax"
    assert {"lateral_separation_m", "camera_angle_deg", "apparent_shift_cm", "note"} <= set(s)
