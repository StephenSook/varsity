"""Chain-of-Grounding provenance manifest: one auditable record per explanation.

Assembles the pieces the pipeline ALREADY produces - the retrieved IFAB Law, the Law-11 proof
steps, the geometry margin + uncertainty, and the Granite + Guardian + verification results -
into a single, tamper-evident manifest that links every fan-facing claim to a concrete fact and
an IFAB clause. This is faithfulness made auditable: a judge, or a fan via "VARSITY, source",
can trace each spoken claim to its grounding and to a SHA-256 over the whole chain.

It ASSEMBLES existing outputs; it never recomputes, second-guesses, or adjudicates the decision.
The manifest carries the grounding chain (proof steps + Law + corpus + models + verification),
not the model's wording, so its hash is stable across phrasing - the grounding is what is
certified, not the prose.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace

_CORPUS = "IFAB Laws of the Game 2025/26"
_GUARDIAN_MODEL = "ibm/granite-guardian-3-8b"


@dataclass(frozen=True)
class GroundingLink:
    claim: str
    law_clause: str
    evidence: str
    source: str


@dataclass(frozen=True)
class ProvenanceManifest:
    decision_id: str
    source: str
    law: str
    law_title: str
    corpus: str
    model: str
    guardian_model: str
    grounded: bool
    proof_consistent: bool
    verified: bool
    links: list[GroundingLink]
    margin_meters: float | None = None
    sigma_meters: float | None = None
    p_verdict: float | None = None
    manifest_hash: str = ""


def _hash(payload: dict) -> str:
    """SHA-256 over the canonical manifest (excluding the hash field itself)."""
    body = {k: v for k, v in payload.items() if k != "manifest_hash"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def links_from_proof(proof_steps: list[dict]) -> list[GroundingLink]:
    """Each Law-11 proof step becomes a claim grounded in its clause + the freeze-frame."""
    status_word = {"pass": "met", "fail": "not met", "n/a": "not applicable"}
    return [
        GroundingLink(
            claim=s["claim"],
            law_clause=f"Law {s.get('law', '11')}",
            evidence=f"{status_word.get(s.get('status', ''), 'noted')} in the Law 11 proof",
            source="StatsBomb 360 freeze-frame",
        )
        for s in proof_steps
    ]


def link_from_law(*, law: str, law_title: str, law_text: str) -> GroundingLink:
    """The spoken explanation is grounded in the governing Law text retrieved from the corpus."""
    snippet = " ".join((law_text or "").split())[:120]
    return GroundingLink(
        claim="The explanation is grounded in the governing Law.",
        law_clause=f"Law {law}",
        evidence=f'retrieved IFAB {law_title}: "{snippet}..."',
        source=_CORPUS,
    )


def build_manifest(
    *,
    decision_id: str,
    source: str,
    law: str,
    law_title: str,
    model: str,
    grounded: bool,
    verified: bool,
    links: list[GroundingLink],
    proof_consistent: bool = True,
    margin_meters: float | None = None,
    sigma_meters: float | None = None,
    p_verdict: float | None = None,
    guardian_model: str = _GUARDIAN_MODEL,
    corpus: str = _CORPUS,
) -> ProvenanceManifest:
    base = ProvenanceManifest(
        decision_id=decision_id,
        source=source,
        law=law,
        law_title=law_title,
        corpus=corpus,
        model=model,
        guardian_model=guardian_model,
        grounded=grounded,
        proof_consistent=proof_consistent,
        verified=verified,
        links=links,
        margin_meters=margin_meters,
        sigma_meters=sigma_meters,
        p_verdict=p_verdict,
    )
    return replace(base, manifest_hash=_hash(asdict(base)))


def provenance_stage(manifest: ProvenanceManifest) -> dict:
    """SSE stage payload for the Chain-of-Grounding manifest."""
    payload = asdict(manifest)
    payload["stage"] = "provenance"
    payload["link_count"] = len(manifest.links)
    return payload
