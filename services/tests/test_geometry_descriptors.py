"""Tests for the descriptive geometry layer (exact predicate + line descriptors)."""

from app import geometry_descriptors as gd
from app.geometry import FreezeFramePlayer


def test_orient2d_exact_sign() -> None:
    assert gd.orient2d_sign(0, 0, 2, 2, 1, 1) == 0  # collinear (level)
    assert gd.orient2d_sign(0, 0, 2, 0, 1, 1) == 1  # c above the rightward line
    assert gd.orient2d_sign(0, 0, 2, 0, 1, -1) == -1  # c below
    # a sub-picometre offset that float cancellation could flip: the exact predicate keeps the sign
    assert gd.orient2d_sign(0.0, 0.0, 1.0, 1.0, 0.5, 0.5 + 1e-12) == 1
    assert gd.orient2d_sign(0.0, 0.0, 1.0, 1.0, 0.5, 0.5 - 1e-12) == -1


def _frame(att_x, defs):
    # one attacker + two opponents minimum; defenders are (x, y)
    players = [FreezeFramePlayer(x=att_x, y=40.0, teammate=True)]
    players += [FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True)]
    players += [FreezeFramePlayer(x=x, y=y, teammate=False) for x, y in defs]
    return players


def test_ahead_sign_matches_the_verdict() -> None:
    # attacker beyond the second-last opponent -> ahead = +1
    offside = _frame(100.0, [(98.0, 20.0), (96.0, 60.0), (119.0, 40.0)])
    assert gd.ahead_of_line_sign(offside) == 1
    # attacker behind the line -> ahead = -1
    onside = _frame(90.0, [(98.0, 20.0), (96.0, 60.0), (119.0, 40.0)])
    assert gd.ahead_of_line_sign(onside) == -1


def test_tilt_is_signed_and_robust() -> None:
    # a back line tilted so deeper-x grows with y has a positive dx/dy tilt
    tilted = _frame(110.0, [(90.0, 10.0), (92.0, 30.0), (94.0, 50.0), (96.0, 70.0)])
    d = gd.describe(tilted)
    assert d.tilt_deg > 1.0
    assert d.thickness_m >= 0 and d.lateral_width_m > 0
    # Theil-Sen (29.3% breakdown) resists one out-of-position defender
    with_outlier = _frame(
        110.0, [(90.0, 10.0), (92.0, 30.0), (94.0, 50.0), (96.0, 70.0), (60.0, 45.0)]
    )
    assert abs(gd.describe(with_outlier).tilt_deg - d.tilt_deg) < 6.0


def test_level_line_has_near_zero_tilt() -> None:
    flat = _frame(110.0, [(95.0, 10.0), (95.0, 30.0), (95.0, 50.0), (95.0, 70.0)])
    assert abs(gd.describe(flat).tilt_deg) < 0.5


def test_payload_shape_and_honest_method() -> None:
    p = gd.payload(_frame(100.0, [(98.0, 20.0), (96.0, 60.0), (119.0, 40.0)]))
    keys = {"n_defenders", "tilt_deg", "thickness_m", "lateral_width_m", "ahead_of_line_sign"}
    assert keys <= set(p)
    assert "Theil-Sen" in p["method"] and "Shewchuk" in p["method"]
    assert "offside line stays the Law-11 perpendicular" in p["method"]


def test_convex_hull_and_area():
    spread = _frame(100.0, [(90.0, 10.0), (95.0, 70.0), (92.0, 40.0), (88.0, 20.0)])
    hull = gd._convex_hull(gd._defenders(spread))
    assert len(hull) >= 3  # a non-degenerate hull
    assert gd._hull_area_m2(gd._defenders(spread)) > 0


def test_free_space_behind_line_is_a_seeded_area():
    f = _frame(100.0, [(98.0, 20.0), (96.0, 60.0), (119.0, 40.0)])
    line_x = gd.second_last_opponent_x(f)
    a1 = gd._free_space_behind_line_m2(f, line_x)
    a2 = gd._free_space_behind_line_m2(f, line_x)
    assert a1 == a2 and a1 > 0  # seeded -> deterministic, and positive behind a high line


def test_stepped_line_grows_with_a_deeper_outlier():
    flat = _frame(110.0, [(95.0, 10.0), (95.0, 30.0), (95.0, 50.0)])
    stepped = _frame(110.0, [(95.0, 10.0), (95.0, 30.0), (85.0, 50.0)])
    assert gd._line_step_m(gd._back_line(stepped)) > gd._line_step_m(gd._back_line(flat))


def test_new_descriptors_in_payload():
    p = gd.payload(_frame(100.0, [(98.0, 20.0), (96.0, 60.0), (119.0, 40.0)]))
    assert {"hull_area_m2", "free_space_behind_line_m2", "line_step_m"} <= set(p)
    assert "free-space-behind-the-line" in p["method"]


def test_defensive_grouping_splits_two_clusters_but_not_a_blob():
    # H0-persistence (MST-gap): two clusters far apart -> 2 groups; a tight blob stays 1
    two = _frame(110.0, [(90, 10), (91, 12), (92, 11), (70, 70), (71, 72), (72, 71)])
    assert gd._defensive_grouping(gd._defenders(two))["defensive_groups"] == 2
    blob = _frame(110.0, [(90, 40), (92, 41), (91, 38), (93, 39), (89, 41)])
    assert gd._defensive_grouping(gd._defenders(blob))["defensive_groups"] == 1


def test_block_concavity_one_on_a_line_and_below_one_on_an_l_shape():
    # robust alpha-shape: a collinear line reports no concavity (1.0); an L-shape is concave (<1)
    flat = _frame(110.0, [(95, 10), (95, 30), (95, 50), (95, 70)])
    assert gd._block_concavity_ratio(gd._defenders(flat)) == 1.0
    el = _frame(110.0, [(80, 20), (82, 20), (84, 20), (86, 20), (80, 40), (80, 60), (80, 75)])
    assert gd._block_concavity_ratio(gd._defenders(el)) < 1.0


def test_delaunay_is_exact_on_a_cocircular_quad():
    # four cocircular points: the exact in-circle predicate must triangulate the convex quad into 2
    tris, _ = gd._delaunay([(0.0, 1.0), (1.0, 0.0), (0.0, -1.0), (-1.0, 0.0)])
    assert len(tris) == 2


def test_grouping_and_concavity_in_payload():
    p = gd.payload(_frame(100.0, [(98.0, 20.0), (96.0, 60.0), (119.0, 40.0)]))
    keys = {"defensive_groups", "largest_gap_m", "split_radius_m", "block_concavity_ratio"}
    assert keys <= set(p)
    assert "MST-gap" in p["method"] and "alpha-shape" in p["method"]


def test_descriptors_survive_degenerate_defender_clouds():
    # the exact Delaunay + MST-gap + concavity must never crash on a collapsed/collinear cloud
    degenerate = [
        [(95, 30), (95, 50)],  # two points
        [(90, 40), (90, 40), (90, 40), (90, 40)],  # all identical
        [(95, 10), (95, 30), (95, 50), (95, 70)],  # collinear vertical
        [(80, 40), (90, 40), (100, 40)],  # collinear horizontal
        [(90.0, 40.0), (90.001, 40.0), (90.0, 40.001)],  # a near-coincident cluster
    ]
    for defs in degenerate:
        d = gd._defenders(_frame(110.0, defs))
        gd._defensive_grouping(d)  # no crash
        c = gd._block_concavity_ratio(d)
        assert 0.0 <= c <= 1.0
        gd.payload(_frame(110.0, defs))  # the full payload (>= 2 opponents) never raises


def _frame_attacker_at_y(att_y):
    # the most-advanced attacker (largest x) sits at the chosen y; the rest is a legal frame
    return [
        FreezeFramePlayer(x=110.0, y=att_y, teammate=True),
        FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=98.0, y=20.0, teammate=False),
        FreezeFramePlayer(x=96.0, y=60.0, teammate=False),
        FreezeFramePlayer(x=119.0, y=40.0, teammate=False),
    ]


def test_lateral_zone_maps_attacker_y_to_channel_and_touchline() -> None:
    # 80-yard width split in thirds: left < 26.67, central, right > 53.33 (left/right are the
    # attacking team's, attack normalised left-to-right).
    assert gd.lateral_zone(_frame_attacker_at_y(0.0))["channel"] == "left"
    assert gd.lateral_zone(_frame_attacker_at_y(20.0))["channel"] == "left"
    assert gd.lateral_zone(_frame_attacker_at_y(40.0))["channel"] == "central"
    assert gd.lateral_zone(_frame_attacker_at_y(60.0))["channel"] == "right"
    assert gd.lateral_zone(_frame_attacker_at_y(80.0))["channel"] == "right"
    # the touchline distance is symmetric and unambiguous: 0 at the line, max at the centre
    assert gd.lateral_zone(_frame_attacker_at_y(0.0))["near_touchline_m"] == 0.0
    assert gd.lateral_zone(_frame_attacker_at_y(80.0))["near_touchline_m"] == 0.0
    centre = gd.lateral_zone(_frame_attacker_at_y(40.0))
    assert centre["near_touchline_m"] == round(40.0 * gd.METERS_PER_UNIT, 1)
    assert "central channel" in centre["phrase"]
    assert "wing" in gd.lateral_zone(_frame_attacker_at_y(10.0))["phrase"]
