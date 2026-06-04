from app.uncertainty import SIGMA_MARGIN_M, quantify


def test_clear_offside_is_virtually_certain() -> None:
    u = quantify(5.45)
    assert u.band == "clear"
    assert u.p_verdict > 0.99
    assert u.likelihood == "virtually certain"
    assert abs(u.sigma_meters - 0.553) < 0.01  # the honest broadcast sigma, not the optical 0.127


def test_razor_tight_is_within_measurement_noise() -> None:
    # 2 cm, well inside the ~55 cm broadcast sigma -> essentially a coin flip on geometry
    u = quantify(0.02)
    assert u.band == "very tight"
    assert u.p_verdict < 0.6
    assert u.likelihood == "about as likely as not"
    assert "Umpire's Call" in u.note


def test_band_thresholds_are_sigma_grounded() -> None:
    s = SIGMA_MARGIN_M
    assert quantify(3 * s).band == "clear"  # > 2 sigma
    assert quantify(1.5 * s).band == "tight"  # between sigma and 2 sigma
    assert quantify(0.5 * s).band == "very tight"  # within sigma


def test_counterfactual_is_the_margin_magnitude() -> None:
    assert quantify(-3.01).counterfactual_meters == 3.01
    assert quantify(0.02).counterfactual_meters == 0.02


def test_onside_clear_is_also_virtually_certain() -> None:
    u = quantify(-3.01)
    assert u.band == "clear"
    assert u.p_verdict > 0.99


def test_confidence_band_schema_and_defer_to_official() -> None:
    # the honest three-band schema + the defer flag for a too-close call
    assert quantify(5.69).confidence_band == "clear"
    assert quantify(5.69).defer_to_official is False
    assert quantify(1.5 * SIGMA_MARGIN_M).confidence_band == "marginal"
    too_close = quantify(0.02)
    assert too_close.confidence_band == "too_close_to_call"
    assert too_close.defer_to_official is True


def test_band_sigma_is_the_honest_broadcast_budget_not_optical() -> None:
    # The band drives spoken confidence + the structured p_verdict off the HONEST broadcast sigma
    # (~0.55 m), ONE source shared with the gum.py budget; the optical ~0.13 m is the comparison.
    from app.gum import SIGMA_MARGIN_GUM_M
    from app.uncertainty import SIGMA_MARGIN_OPTICAL_M

    assert SIGMA_MARGIN_M == SIGMA_MARGIN_GUM_M  # one source, no drift
    assert 0.5 < SIGMA_MARGIN_M < 0.6
    assert SIGMA_MARGIN_OPTICAL_M < SIGMA_MARGIN_M and abs(SIGMA_MARGIN_OPTICAL_M - 0.127) < 0.01
    # a 30 cm offside is honestly too close to call on coarse broadcast data ...
    assert quantify(0.30).confidence_band == "too_close_to_call"
    # ... while the clear demo call (5.69 m) stays clear: the core demo is unaffected.
    assert quantify(5.69).confidence_band == "clear"


def test_measured_literature_envelope_brackets_the_point_sigma() -> None:
    # the measured-literature sigma envelope (low/high inputs) must bracket the point estimate, so
    # the sensitivity receipt sweeps a range the point value sits inside.
    from app.uncertainty import margin_sigma_bounds

    lo, hi = margin_sigma_bounds()
    assert lo < SIGMA_MARGIN_M < hi
    assert 0.2 < lo < 0.35 and 1.0 < hi < 1.3  # ~[0.26, 1.18] from the measured input ranges
