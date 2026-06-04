"""Tests for the GUM uncertainty budget (the rigorous superset of the band)."""

import math

from app import gum, uncertainty


def test_propagation_minus_sign_shrinks_the_difference() -> None:
    # GUM Eq (16) for a difference: u_c^2 = u_a^2 + u_d^2 - 2 r u_a u_d. Positive correlation
    # (shared homography error) must REDUCE the combined uncertainty of the margin. The primitive
    # now lives in uncertainty.py (one source the GUM budget builds on).
    independent = uncertainty.combined_position_uncertainty(0.6, 0.6, 0.0)
    correlated = uncertainty.combined_position_uncertainty(0.6, 0.6, 0.7)
    assert correlated < independent
    assert math.isclose(independent, math.sqrt(0.72), rel_tol=1e-6)  # sqrt(2)*0.6


def test_two_regime_sigmas() -> None:
    # the honest broadcast-annotation regime is much wider than the optical-tracking equivalent
    assert gum.SIGMA_MARGIN_GUM_M > gum.SIGMA_MARGIN_OPTICAL_M
    assert 0.4 < gum.SIGMA_MARGIN_GUM_M < 0.8
    assert math.isclose(gum.SIGMA_MARGIN_OPTICAL_M, round(math.sqrt(2) * 0.09, 3), abs_tol=0.005)


def test_clear_offside_is_secure_and_low_entropy() -> None:
    b = gum.budget(5.69)
    assert b.coverage_interval_m[0] > 0  # the whole coverage interval is offside
    assert b.straddles_zero is False
    assert b.p_offside == 1.0
    assert b.entropy_bits < 0.05 and b.verbosity == "concise"


def test_tight_call_coverage_straddles_zero_and_max_entropy() -> None:
    # the honest payoff: a knife-edge margin's coverage interval straddles the line, so it is
    # too close to call and the entropy is ~1 bit (a coin flip).
    b = gum.budget(0.02)
    assert b.straddles_zero is True
    assert b.coverage_interval_m[0] < 0 < b.coverage_interval_m[1]
    assert b.entropy_bits > 0.95 and b.verbosity == "rich"


def test_clear_onside_supports_offside_near_zero() -> None:
    b = gum.budget(-3.14)
    assert b.p_offside < 0.01
    assert b.coverage_interval_m[1] < 0  # the whole interval is onside


def test_entropy_bits_bounds() -> None:
    assert gum.entropy_bits(0.5) == 1.0
    assert gum.entropy_bits(0.0) == 0.0 and gum.entropy_bits(1.0) == 0.0
    assert 0.0 < gum.entropy_bits(0.9) < 0.5


def test_monte_carlo_agrees_with_closed_form() -> None:
    # the seeded GUM-S1 Monte-Carlo P(offside) must agree with the closed-form Phi within a few %
    b = gum.budget(0.30)
    assert abs(b.mc_p_offside - b.p_offside) < 0.03
    assert b.mc_ci[0] <= b.mc_p_offside <= b.mc_ci[1]


def test_temperature_matches_logistic_approximation() -> None:
    # T = sigma_m / 1.7 (Phi ~= logistic(1.7 x)); the budget reports it
    b = gum.budget(1.0)
    assert math.isclose(b.temperature_m, round(gum.SIGMA_MARGIN_GUM_M / 1.7, 3), abs_tol=1e-3)


def test_payload_is_serializable_and_cited() -> None:
    p = gum.payload(5.69, is_offside=True)
    assert p["coverage_factor_k"] == 2.0
    assert "JCGM 100:2008" in p["sources"] and "Jaynes" in p["sources"]
    assert p["regimes"]["optical_equivalent_sigma_m"] < p["regimes"]["broadcast_annotation_sigma_m"]
    assert len(p["coverage_interval_m"]) == 2 and len(p["credible_interval_m"]) == 2
    assert "spoken" in p and "offside" in p["spoken"]


def test_ipcc_hedge_pairs_word_with_numeric_range() -> None:
    word, rng = gum.ipcc_hedge(0.999)
    assert word == "virtually certain" and rng == "99 to 100 percent"
    assert gum.ipcc_hedge(0.92)[0] == "very likely"
    assert gum.ipcc_hedge(0.55)[0] == "more likely than not"


def test_spoken_narration_speaks_the_coverage_and_hedge_with_range() -> None:
    # a clear offside: the verdict word + the IPCC hedge WITH its numeric range (Budescu) + the
    # explicit coverage interval, all deterministic (never from the LLM)
    clear = gum.spoken_narration(5.69, is_offside=True)
    assert "virtually certain" in clear and "99 to 100 percent" in clear
    assert "coverage interval" in clear and "offside" in clear


def test_spoken_narration_is_honest_and_rich_on_a_close_call() -> None:
    tight = gum.spoken_narration(0.02, is_offside=True)
    assert "close call" in tight and "bits" in tight
    assert "straddling" in tight and "trusts the official" in tight


def test_spoken_narration_handles_the_onside_direction() -> None:
    onside = gum.spoken_narration(-3.14, is_offside=False)
    assert "onside" in onside and "virtually certain" in onside


def test_fitted_temperature_recovers_the_closed_form() -> None:
    # fitting the Boltzmann temperature to reproduce Phi recovers the analytic T = sigma/1.7
    r = gum.fitted_temperature()
    assert r["agree"] is True
    assert abs(r["fitted_temperature_m"] - r["closed_form_temperature_m"]) < 0.05


def test_student_t_sensitivity_is_robust_for_clear_and_tight() -> None:
    assert gum.student_t_sensitivity(5.69)["robust"] is True
    tight = gum.student_t_sensitivity(0.02)
    assert tight["robust"] is True  # even a knife-edge call shifts < 2 pp under heavy tails
    assert abs(tight["shift_percentage_points"]) < 2.0


def test_extended_payload_carries_robustness_receipts_only_on_demand() -> None:
    ext = gum.payload(0.02, is_offside=True, extended=True)
    assert "student_t_sensitivity" in ext and "fitted_temperature" in ext
    # the per-stream SSE stage stays light (no heavy receipts)
    assert "student_t_sensitivity" not in gum.payload(0.02, is_offside=True)


def test_spoken_line_never_contradicts_the_verdict_band() -> None:
    # the two uncertainty layers must tell one story: for a margin the calibrated band reads as
    # clear/marginal, the GUM broadcast budget can still straddle zero, but the spoken line must NOT
    # then say "trusts the official" (which would contradict the confident spoken verdict).
    from app.uncertainty import quantify

    # margins above the band sigma (~0.55 m) but inside the GUM coverage interval (~1.1 m): the
    # budget straddles zero while the band reads clear/marginal, so the two layers must not clash.
    for m in (0.6, 0.75, 0.9, 1.0):
        assert gum.budget(m).straddles_zero  # the wider broadcast budget does straddle here
        assert quantify(m).band != "very tight"  # but the calibrated band is not too-close
        assert "trusts the official" not in gum.spoken_narration(m, is_offside=True)
    # a genuinely very-tight call still withholds and defers
    assert "trusts the official" in gum.spoken_narration(0.02, is_offside=True)


def test_ipcc_hedge_covers_the_full_symmetric_scale() -> None:
    # the lower half must exist: a low probability is "unlikely", never a false "more likely than
    # not" (the old bands stopped at 0.5 and fell through to that fallback for every p < 0.5).
    assert gum.ipcc_hedge(1.0)[0] == "virtually certain"
    assert gum.ipcc_hedge(0.55)[0] == "more likely than not"
    assert gum.ipcc_hedge(0.40)[0] == "about as likely as not"
    assert gum.ipcc_hedge(0.20)[0] == "unlikely"
    assert gum.ipcc_hedge(0.0)[0] == "exceptionally unlikely"


def test_spoken_line_for_data_contradicting_the_official_is_not_falsely_confident() -> None:
    # geometry clearly onside (-3 m) but the official called offside: the data's support for that
    # verdict is ~0, so the spoken line must read "unlikely", not "more likely than not".
    line = gum.spoken_narration(-3.0, is_offside=True)
    assert "more likely than not" not in line
    assert "unlikely" in line


def test_sigma_sensitivity_demo_is_robust_across_the_measured_envelope() -> None:
    # the clear demo call (5.69 m) reads "clear" at EVERY sigma in the measured-literature envelope,
    # so the verdict does not hinge on the exact (partly-unmeasured) sigma.
    s = gum.sigma_sensitivity(5.69)
    assert s["band_robust"] is True
    assert s["bands_seen"] == ["clear"]
    lo, hi = s["sigma_envelope_m"]
    assert lo < s["point_sigma_m"] < hi  # the point estimate sits inside the envelope


def test_sigma_sensitivity_surfaces_a_margin_dependent_call_honestly() -> None:
    # a 30 cm call is NOT robust across the envelope (marginal at the optimistic end, too-close at
    # the pessimistic end); the receipt must surface that rather than hide it behind one number.
    s = gum.sigma_sensitivity(0.30)
    assert s["band_robust"] is False
    assert len(s["bands_seen"]) > 1
