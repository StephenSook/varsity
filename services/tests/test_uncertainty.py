from app.uncertainty import SIGMA_MARGIN_M, quantify


def test_clear_offside_is_virtually_certain() -> None:
    u = quantify(5.45)
    assert u.band == "clear"
    assert u.p_verdict > 0.99
    assert u.likelihood == "virtually certain"
    assert abs(u.sigma_meters - 0.127) < 0.01


def test_razor_tight_is_within_measurement_noise() -> None:
    # 2 cm, well inside the ~13 cm propagated sigma -> essentially a coin flip on geometry
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
