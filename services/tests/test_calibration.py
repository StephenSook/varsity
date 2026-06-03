"""Tests for the confidence-calibration receipt (ECE / Brier / reliability diagram)."""

from __future__ import annotations

from app.calibration import build_report, predicted_confidence
from app.uncertainty import SIGMA_MARGIN_M


def test_predicted_confidence_is_never_below_half():
    # Phi(|m| / sigma) >= 0.5 always: the model is never under 50% sure of its own verdict.
    for m in (-0.5, -0.1, 0.0, 0.05, 0.3):
        assert predicted_confidence(m, SIGMA_MARGIN_M) >= 0.5


def test_well_specified_model_is_calibrated():
    # Under the stated noise model the reported confidence is calibrated by construction.
    assert build_report().ece < 0.01


def test_overconfident_control_is_visibly_miscalibrated():
    r = build_report()
    assert r.overconfident_ece > 5 * r.ece  # ~12x worse in practice - strongly discriminating
    assert r.overconfident_ece > 0.03  # a halved-sigma model visibly fails the diagram


def test_brier_is_in_the_unit_interval():
    assert 0.0 <= build_report().brier <= 1.0


def test_report_is_deterministic():
    a, b = build_report(), build_report()
    assert a.ece == b.ece and a.brier == b.brier
    assert [bn.count for bn in a.bins] == [bn.count for bn in b.bins]


def test_bins_cover_all_samples_and_accuracy_rises_with_confidence():
    r = build_report()
    assert sum(b.count for b in r.bins) == r.samples
    populated = [b for b in r.bins if b.count]
    # The highest-confidence bin is at least as accurate as the lowest populated one.
    assert populated[-1].empirical_accuracy >= populated[0].empirical_accuracy


def test_calibration_endpoint_serves_the_receipt():
    from fastapi.testclient import TestClient

    from app.main import app

    res = TestClient(app).get("/calibration")
    assert res.status_code == 200
    j = res.json()
    assert j["ece"] < 0.01
    assert j["overconfident_ece"] > j["ece"]
    assert len(j["bins"]) == 10
    assert j["sigma_true_cm"] == round(SIGMA_MARGIN_M * 100, 1)
