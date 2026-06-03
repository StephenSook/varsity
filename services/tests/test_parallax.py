import math

from app import parallax
from app.geometry import FreezeFramePlayer

_X = 105.0 / 120.0
_Y = 68.0 / 80.0
_CAM = (52.5, -25.0, 18.0)


def _frame(ax=100.0, ay=40.0, def2_x=98.0):
    return [
        FreezeFramePlayer(x=ax, y=ay, teammate=True),
        FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=def2_x, y=42.0, teammate=False),
        FreezeFramePlayer(x=119.0, y=40.0, teammate=False, keeper=True),
    ]


def _expected(ax, ay):
    axm, aym = ax * _X, ay * _Y
    cx, cy, cz = _CAM
    d = round(math.sqrt((axm - cx) ** 2 + (aym - cy) ** 2 + cz**2), 1)
    shift = min(d * math.tan(math.radians(0.2)), 0.6)
    return d, round(shift * 100)


def test_distance_and_shift_match_projection() -> None:
    out = parallax.estimate(_frame(100.0, 40.0))
    d, cm = _expected(100.0, 40.0)
    assert out["camera_distance_m"] == d
    assert out["apparent_shift_cm"] == cm
    assert out["residual_angle_deg"] == 0.2


def test_shift_is_bounded_tens_of_cm() -> None:
    # any on-pitch attacker -> a sane, bounded apparent shift (never metres of nonsense)
    for ax, ay in [(60.0, 5.0), (118.0, 78.0), (90.0, 40.0)]:
        cm = parallax.estimate(_frame(ax, ay))["apparent_shift_cm"]
        assert 0 < cm <= 60


def test_farther_incident_shifts_more() -> None:
    near = parallax.estimate(_frame(60.0, 40.0))["apparent_shift_cm"]
    far = parallax.estimate(_frame(118.0, 40.0))["apparent_shift_cm"]
    assert far >= near


def test_note_does_not_re_adjudicate() -> None:
    note = parallax.estimate(_frame())["note"].lower()
    assert "camera" in note and "real tracked positions" in note
    assert "onside" not in note  # never asserts a verdict


def test_stage_shape() -> None:
    s = parallax.parallax_stage(_frame())
    assert s["stage"] == "parallax"
    assert {"camera_distance_m", "residual_angle_deg", "apparent_shift_cm", "note"} <= set(s)
