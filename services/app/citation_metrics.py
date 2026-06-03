"""ALCE-style citation precision/recall over the Chain-of-Grounding provenance manifest.

ALCE (Gao, Yen, Yu & Chen, EMNLP 2023, "Enabling Large Language Models to Generate Text with
Citations") measures whether a cited source ENTAILS the statement it supports:
- citation RECALL = fraction of claims that have at least one supporting citation;
- citation PRECISION = fraction of citations that actually support their claim (an irrelevant or
  spurious citation lowers it).

We run a DETERMINISTIC entailment proxy (no NLI model loads on the Render free tier): a citation
supports its claim iff it is a concrete Law citation, the claim is substantive, and the cited
clause's salient terms appear in the claim - the same mechanical relevance idea as the
grounded-in-law critic. It is a METRIC over what the pipeline ALREADY emits (``provenance.py``),
and it DISCRIMINATES: a spurious citation (right claim, wrong clause) drops precision and a claim
with no citation drops recall - both shown as controls, so the metric is not vacuous.

In-concept: it scores the ATTRIBUTION of the explanation of a received decision; it never
adjudicates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.provenance import GroundingLink

_LAW_CITATION = re.compile(r"law\s+\d", re.IGNORECASE)
_DESCRIPTOR = re.compile(r"\(([^)]+)\)")
# words in a clause descriptor that carry no relevance signal (relations / articles).
_STOP = {"the", "a", "an", "of", "with", "to", "by", "in", "and", "or", "than", "beyond", "nearer"}


def _tokens(text: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def supports(link: GroundingLink) -> bool:
    """Deterministic entailment proxy: does this citation support its claim?"""
    if not _LAW_CITATION.search(link.law_clause):
        return False  # not a concrete Law citation
    if len(link.claim.split()) < 3 or not link.evidence.strip():
        return False  # not a substantive, evidenced claim
    descriptor = _DESCRIPTOR.search(link.law_clause)
    if descriptor:
        salient = _tokens(descriptor.group(1)) - _STOP
        # the cited clause's salient terms must appear in the claim (citation is relevant).
        return bool(salient & _tokens(link.claim))
    # a clause-less Law citation (e.g. the governing-Law grounding link) is supported when it
    # carries a retrieved quote rather than an unsupported assertion.
    ev = link.evidence.lower()
    return "retrieved" in ev or '"' in link.evidence


@dataclass(frozen=True)
class CitationReport:
    claims: int
    citations: int
    supported: int
    recall: float  # claims with >= 1 supporting citation / claims
    precision: float  # supporting citations / citations
    unsupported_claims: list[str]


def score(links: list[GroundingLink]) -> CitationReport:
    """ALCE precision/recall over the manifest links (each link = one claim, one citation)."""
    if not links:
        return CitationReport(0, 0, 0, 1.0, 1.0, [])
    supported = [link for link in links if supports(link)]
    unsupported = [link.claim for link in links if not supports(link)]
    n = len(links)
    return CitationReport(
        claims=n,
        citations=n,
        supported=len(supported),
        recall=round(len(supported) / n, 3),
        precision=round(len(supported) / n, 3),
        unsupported_claims=unsupported,
    )


def _controls() -> dict:
    """Show the metric discriminates: a spurious citation drops precision; a dangling claim
    (no real citation) drops recall. Demonstrative, not part of the live manifest."""
    real = GroundingLink(
        claim="Nearer the goal line than the second-to-last opponent.",
        law_clause="Law 11.1 (beyond the second-to-last opponent)",
        evidence="met in the Law 11 proof",
        source="StatsBomb 360 freeze-frame",
    )
    spurious = GroundingLink(  # right claim, WRONG clause - precision must drop
        claim="Nearer the goal line than the second-to-last opponent.",
        law_clause="Law 14 (penalty kick)",
        evidence="met in the Law 11 proof",
        source="StatsBomb 360 freeze-frame",
    )
    dangling = GroundingLink(  # no concrete Law citation - recall must drop
        claim="The attacker was clearly past the line.",
        law_clause="(no clause)",
        evidence="",
        source="",
    )
    return {
        "well_formed_precision": score([real]).precision,
        "spurious_citation_precision": score([real, spurious]).precision,
        "dangling_claim_recall": score([real, dangling]).recall,
    }


def citation_metrics_stage(links: list[GroundingLink]) -> dict:
    """The SSE 'citation_metrics' stage payload (ALCE precision/recall + controls)."""
    report = score(links)
    return {
        "stage": "citation_metrics",
        "claims": report.claims,
        "citations": report.citations,
        "supported": report.supported,
        "recall": report.recall,
        "precision": report.precision,
        "unsupported_claims": report.unsupported_claims,
        "controls": _controls(),
        "note": (
            "ALCE-style citation precision/recall over the provenance manifest, via a "
            "deterministic entailment proxy (the cited Law clause's salient terms must appear in "
            "the claim). Controls confirm a spurious citation drops precision and a dangling "
            "claim drops recall."
        ),
    }
