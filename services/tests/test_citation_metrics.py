"""Tests for the ALCE-style citation precision/recall over the provenance manifest."""

from __future__ import annotations

from app.citation_metrics import citation_metrics_stage, score, supports
from app.law11 import proof_payload, prove
from app.provenance import GroundingLink, link_from_law, links_from_proof


def _real_manifest_links():
    proof = prove(
        is_offside=True,
        margin_meters=0.3,
        beyond_defender=True,
        beyond_ball=True,
        attacker_x=100.0,
    )
    return links_from_proof(proof_payload(proof)["steps"]) + [
        link_from_law(
            law="11", law_title="Offside", law_text="A player is in an offside position..."
        )
    ]


def test_real_manifest_is_fully_supported():
    report = score(_real_manifest_links())
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.unsupported_claims == []


def test_spurious_citation_drops_precision():
    real = GroundingLink(
        claim="Nearer the goal line than the second-to-last opponent.",
        law_clause="Law 11.1 (beyond the second-to-last opponent)",
        evidence="met in the Law 11 proof",
        source="StatsBomb 360 freeze-frame",
    )
    spurious = GroundingLink(  # right claim, wrong clause
        claim="Nearer the goal line than the second-to-last opponent.",
        law_clause="Law 14 (penalty kick)",
        evidence="met in the Law 11 proof",
        source="StatsBomb 360 freeze-frame",
    )
    assert supports(real) is True
    assert supports(spurious) is False
    assert score([real, spurious]).precision == 0.5


def test_dangling_claim_drops_recall():
    real = GroundingLink(
        claim="Nearer the goal line than the second-to-last opponent.",
        law_clause="Law 11.1 (beyond the second-to-last opponent)",
        evidence="met in the Law 11 proof",
        source="StatsBomb 360 freeze-frame",
    )
    dangling = GroundingLink(
        claim="The attacker was clearly past the line.",
        law_clause="(no clause)",
        evidence="",
        source="",
    )
    assert score([real, dangling]).recall == 0.5


def test_stage_carries_discriminating_controls():
    stage = citation_metrics_stage(_real_manifest_links())
    c = stage["controls"]
    assert c["well_formed_precision"] == 1.0
    assert c["spurious_citation_precision"] < 1.0
    assert c["dangling_claim_recall"] < 1.0
