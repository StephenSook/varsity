"""Tests for the GUM uncertainty budget (the rigorous superset of the band)."""

import math

from app import gum


def test_propagation_minus_sign_shrinks_the_difference() -> None:
    # GUM Eq (16) for a difference: u_c^2 = u_a^2 + u_d^2 - 2 r u_a u_d. Positive correlation
    # (shared homography error) must REDUCE the combined uncertainty of the margin.
    independent = gum.combined_position_uncertainty(0.6, 0.6, 0.0)
    correlated = gum.combined_position_uncertainty(0.6, 0.6, 0.7)
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
    p = gum.payload(5.69)
    assert p["coverage_factor_k"] == 2.0
    assert "JCGM 100:2008" in p["sources"] and "Jaynes" in p["sources"]
    assert p["regimes"]["optical_equivalent_sigma_m"] < p["regimes"]["broadcast_annotation_sigma_m"]
    assert len(p["coverage_interval_m"]) == 2 and len(p["credible_interval_m"]) == 2
