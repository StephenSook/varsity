"""The VARSITY explanation pipeline: geometry -> Law retrieval -> Granite -> Guardian.

``explanation_stages`` is a generator that yields one dict per stage, so the SSE
endpoint can stream the pipeline unfolding (and the front end can render both the
spoken verdict and the per-stage trace). Clients are injectable for offline tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from app import (
    causal,
    citation_metrics,
    completeness,
    discourse,
    geometry_descriptors,
    gum,
    law11,
    parallax,
    provenance,
    verbalizer,
    verification,
    walton,
)
from app.decisions import get_decision
from app.geometry import FreezeFramePlayer, compute_offside
from app.llm.granite import GraniteClient
from app.llm.guardian import GuardianClient
from app.observability import tracer
from app.rag.retriever import LawRetriever
from app.safety import input_screen
from app.signals import referee_signal
from app.uncertainty import quantify

OFFSIDE_QUERY = "offside attacker nearer the goal line than the second-last defender and the ball"


def _confidence(margin_meters: float) -> str:
    """How clear-cut the call is, grounded in the honest measurement-noise band (uncertainty)."""
    return quantify(margin_meters).band


def _uncertainty_fields(margin_meters: float) -> dict:
    """The 'VARSITY's Call' uncertainty payload shared by the geometry + verdict stages."""
    unc = quantify(margin_meters)
    return {
        "confidence": unc.band,
        "confidence_band": unc.confidence_band,
        "defer_to_official": unc.defer_to_official,
        "sigma_meters": unc.sigma_meters,
        "p_verdict": unc.p_verdict,
        "likelihood": unc.likelihood,
        "counterfactual_meters": unc.counterfactual_meters,
        "uncertainty_note": unc.note,
    }


@dataclass
class PipelineResult:
    is_offside: bool
    margin_meters: float
    law: str
    law_title: str
    explanation: str
    safe: bool
    cites_law: bool
    grounded: bool = True


def explanation_stages(
    frame: list[FreezeFramePlayer],
    *,
    language: str = "English",
    retriever: LawRetriever | None = None,
    granite: object | None = None,
    guardian: object | None = None,
    trigger_meta: dict | None = None,
    prewarmed_law: object | None = None,
) -> Iterator[dict]:
    retriever = retriever or LawRetriever()
    granite = granite or GraniteClient()
    guardian = guardian or GuardianClient()

    yield {"stage": "trigger", **(trigger_meta or {"source": "StatsBomb 360 (canned)"})}

    with tracer.start_as_current_span("geometry") as span:
        geo = compute_offside(frame)
        span.set_attribute("varsity.is_offside", geo.is_offside)
        span.set_attribute("varsity.margin_meters", geo.margin_meters)
    yield {
        "stage": "geometry",
        "margin_meters": geo.margin_meters,
        "is_offside": geo.is_offside,
        **_uncertainty_fields(geo.margin_meters),
        "offside_line_x": geo.offside_line_x,
        "attacker_x": geo.attacker_x,
        "pitch": {"length": 120, "width": 80},
        "players": [
            {
                "x": p.x,
                "y": p.y,
                "teammate": p.teammate,
                "actor": p.actor,
                "keeper": p.keeper,
            }
            for p in frame
        ],
    }

    # GUM uncertainty budget: the honest broadcast-data coverage interval, Bayesian credible
    # interval, Shannon entropy, and Monte-Carlo cross-check (the rigorous superset of the band).
    yield {
        "stage": "uncertainty_budget",
        **gum.payload(geo.margin_meters, is_offside=geo.is_offside),
    }

    # Descriptive geometry: the defensive line's tilt + thickness + width + an exact-rational
    # "ahead-of-line" predicate. Describes the spatial context; never redefines the offside line.
    yield {"stage": "geometry_descriptors", **geometry_descriptors.payload(frame)}

    # Discourse cohesion: reference the decisions already explained earlier in this match (records
    # and refers back to RECEIVED decisions; never predicts or recomputes a call).
    _match_id = (trigger_meta or {}).get("match_name", "default")
    _minute = (trigger_meta or {}).get("minute")
    _band = quantify(geo.margin_meters).band
    _key = discourse.moment_key(geo.is_offside, geo.margin_meters)
    _state = discourse.for_match(_match_id)
    _connective = discourse.connective(
        _state, key=_key, is_offside=geo.is_offside, band=_band, minute=_minute
    )
    discourse.record(_state, key=_key, is_offside=geo.is_offside, band=_band, minute=_minute)
    yield {
        "stage": "discourse",
        "connective": _connective,
        "tight_calls_so_far": _state.tight_count,
        "half": discourse.half_label(_minute),
        "decisions_seen": len(_state.history),
    }

    sig = referee_signal(is_offside=geo.is_offside)
    yield {"stage": "signal", "text": sig["text"], "law": sig["law"]}

    within_noise = quantify(geo.margin_meters).band == "very tight"

    # Neuro-symbolic Law-11 proof tree: the auditable rule traversal of the decision.
    proof = law11.prove(
        is_offside=geo.is_offside,
        margin_meters=geo.margin_meters,
        beyond_defender=geo.beyond_defender,
        beyond_ball=geo.beyond_ball,
        attacker_x=geo.attacker_x,
        within_noise=within_noise,
    )
    proof_dict = law11.proof_payload(proof)
    yield proof_dict

    # Coqatoo-style verbalizer: a faithful-by-construction explanation rendered from the proof
    # alone (no model), emitted alongside the Granite prose so the verdict words can be compared.
    yield verbalizer.verbalize_stage(proof)

    # Camera-parallax explainer: why a correct call can LOOK wrong on a broadcast angle.
    yield parallax.parallax_stage(frame)

    # Halpern-Pearl contrastive opener: why offside RATHER THAN onside, and the decisive cause.
    yield causal.contrastive(
        is_offside=geo.is_offside, margin_meters=geo.margin_meters, within_noise=within_noise
    )

    # Walton critical-questions: the questions a skeptic would ask, answered from the evidence.
    yield walton.critical_questions(
        is_offside=geo.is_offside, margin_meters=geo.margin_meters, within_noise=within_noise
    )

    with tracer.start_as_current_span("law") as span:
        # On the live path the Law is pre-retrieved during the 'reviewing' gap (speculative
        # pre-warm), so the resolved explanation skips this retrieval; the canned path
        # retrieves here as usual. Either way the SAME Law text grounds the explanation.
        law = prewarmed_law or retriever.retrieve(OFFSIDE_QUERY)
        span.set_attribute("varsity.law", law.law)
        span.set_attribute("varsity.law_title", law.title)
        span.set_attribute("varsity.law_prewarmed", prewarmed_law is not None)
    yield {"stage": "law", "law": law.law, "title": law.title, "text": law.text}

    with tracer.start_as_current_span("granite") as span:
        explanation = granite.explain_offside(
            margin_meters=geo.margin_meters,
            is_offside=geo.is_offside,
            law_text=law.text,
            language=language,
            within_noise=within_noise,
        )
        model = getattr(getattr(granite, "config", None), "model_id", "granite")
        # Read synchronously right after the call: "granite" if a live watsonx reply passed the
        # accept-gate, "deterministic-floor" if a watsonx outage degraded to the Law-citing floor.
        # Keeps the trace honest instead of always claiming the model produced the text.
        source = getattr(granite, "last_source", "granite")
        span.set_attribute("varsity.model", model)
        span.set_attribute("varsity.source", source)
        span.set_attribute("varsity.language", language)
    yield {"stage": "granite", "model": model, "source": source}

    with tracer.start_as_current_span("guardian") as span:
        verdict = guardian.check(explanation, law_context=law.text)
        span.set_attribute("varsity.safe", verdict.safe)
        span.set_attribute("varsity.grounded", verdict.grounded)
        span.set_attribute("varsity.screen_reader_ok", verdict.screen_reader_ok)
        span.set_attribute("varsity.guardian_model", getattr(guardian, "model_id", "guardian"))
    yield {
        "stage": "guardian",
        "safe": verdict.safe,
        "cites_law": verdict.cites_law,
        "grounded": verdict.grounded,
        "screen_reader_ok": verdict.screen_reader_ok,
        "answer": verdict.model_answer,
    }

    panel = verification.verify(
        explanation=explanation,
        cites_law=verdict.cites_law,
        grounded=verdict.grounded,
        screen_reader_ok=verdict.screen_reader_ok,
        proof_consistent=proof.consistent_with_decision,
        is_offside=geo.is_offside,
        law_text=law.text,
        within_noise=within_noise,
    )
    yield verification.verification_stage(panel)

    # Argumentative completeness: does the narration DISCLOSE enough for a blind fan (the
    # complement to faithfulness - what it says, not just whether what it says is true).
    yield completeness.completeness_stage(
        completeness.score_offside(explanation, within_noise=within_noise)
    )

    unc = quantify(geo.margin_meters)
    state = "offside" if geo.is_offside else "onside"
    manifest = provenance.build_manifest(
        decision_id=f"{state} {geo.margin_meters:+.2f}m",
        source=(trigger_meta or {}).get("match_name", "StatsBomb 360 (canned)"),
        law=law.law,
        law_title=law.title,
        model=model,
        grounded=verdict.grounded,
        verified=panel.verified,
        proof_consistent=proof.consistent_with_decision,
        links=provenance.links_from_proof(proof_dict["steps"])
        + [provenance.link_from_law(law=law.law, law_title=law.title, law_text=law.text)],
        margin_meters=geo.margin_meters,
        sigma_meters=unc.sigma_meters,
        p_verdict=unc.p_verdict,
        guardian_model=getattr(guardian, "model_id", None)
        or "ibm/granite-guardian-3-8b",
    )
    yield provenance.provenance_stage(manifest)

    # ALCE-style citation precision/recall over the manifest's grounding links.
    yield citation_metrics.citation_metrics_stage(manifest.links)

    yield {
        "stage": "verdict",
        "text": explanation,
        "is_offside": geo.is_offside,
        "law": law.law,
        "law_text": law.text,
        "margin_meters": geo.margin_meters,
        **_uncertainty_fields(geo.margin_meters),
        "safe": verdict.safe,
    }


def decision_stages(
    decision_name: str,
    *,
    language: str = "English",
    retriever: LawRetriever | None = None,
    granite: object | None = None,
    guardian: object | None = None,
) -> Iterator[dict]:
    """Stream a NON-geometry VAR decision (penalty, handball, ...) through the same
    RAG -> Granite -> Guardian path as offside. No geometry stage; a ``decision`` stage
    carries the illustrative incident instead."""
    d = get_decision(decision_name)
    retriever = retriever or LawRetriever()
    granite = granite or GraniteClient()
    guardian = guardian or GuardianClient()

    yield {
        "stage": "trigger",
        "source": "Illustrative VAR incident",
        "decision_type": d["decision_type"],
        "label": d["label"],
        "tier": "illustrative",
    }
    yield {
        "stage": "decision",
        "decision_type": d["decision_type"],
        "incident": d["incident"],
        "outcome": d["outcome"],
    }

    sig = referee_signal(decision_type=d["decision_type"])
    yield {"stage": "signal", "text": sig["text"], "law": sig["law"]}

    with tracer.start_as_current_span("law") as span:
        law = retriever.retrieve(d["law_query"])
        span.set_attribute("varsity.law", law.law)
        span.set_attribute("varsity.law_title", law.title)
    yield {"stage": "law", "law": law.law, "title": law.title, "text": law.text}

    with tracer.start_as_current_span("granite") as span:
        explanation = granite.explain_decision(
            incident=d["incident"],
            outcome=d["outcome"],
            law=law.law,
            law_text=law.text,
            language=language,
        )
        model = getattr(getattr(granite, "config", None), "model_id", "granite")
        source = getattr(granite, "last_source", "granite")
        span.set_attribute("varsity.model", model)
        span.set_attribute("varsity.source", source)
        span.set_attribute("varsity.language", language)
    yield {"stage": "granite", "model": model, "source": source}

    with tracer.start_as_current_span("guardian") as span:
        verdict = guardian.check(explanation, law_context=law.text)
        span.set_attribute("varsity.safe", verdict.safe)
        span.set_attribute("varsity.grounded", verdict.grounded)
        span.set_attribute("varsity.screen_reader_ok", verdict.screen_reader_ok)
        span.set_attribute("varsity.guardian_model", getattr(guardian, "model_id", "guardian"))
    yield {
        "stage": "guardian",
        "safe": verdict.safe,
        "cites_law": verdict.cites_law,
        "grounded": verdict.grounded,
        "screen_reader_ok": verdict.screen_reader_ok,
        "answer": verdict.model_answer,
    }

    panel = verification.verify(
        explanation=explanation,
        cites_law=verdict.cites_law,
        grounded=verdict.grounded,
        screen_reader_ok=verdict.screen_reader_ok,
    )
    yield verification.verification_stage(panel)

    manifest = provenance.build_manifest(
        decision_id=d["decision_type"],
        source="Illustrative VAR incident",
        law=law.law,
        law_title=law.title,
        model=model,
        grounded=verdict.grounded,
        verified=panel.verified,
        links=[provenance.link_from_law(law=law.law, law_title=law.title, law_text=law.text)],
        guardian_model=getattr(guardian, "model_id", None)
        or "ibm/granite-guardian-3-8b",
    )
    yield provenance.provenance_stage(manifest)
    yield citation_metrics.citation_metrics_stage(manifest.links)

    yield {
        "stage": "verdict",
        "text": explanation,
        "decision_type": d["decision_type"],
        "law": law.law,
        "law_text": law.text,
        "outcome": d["outcome"],
        "safe": verdict.safe,
    }


def question_stages(
    question: str,
    *,
    language: str = "English",
    retriever: LawRetriever | None = None,
    granite: object | None = None,
    guardian: object | None = None,
) -> Iterator[dict]:
    """Stream a free-text fan question through retrieve -> Granite (grounded) -> Guardian
    -> verdict: the 'ask any rule' oracle. The retrieved Law is the grounding; Granite
    answers within it and Guardian checks the answer stays grounded."""
    retriever = retriever or LawRetriever()
    granite = granite or GraniteClient()
    guardian = guardian or GuardianClient()

    yield {"stage": "trigger", "source": "Fan question", "question": question}

    # LLM01 input hardening: screen the untrusted free-text BEFORE any model call. On a
    # HAP / prompt-injection hit, FAIL CLOSED - decline (the question is withheld from the
    # model) and emit the terminal verdict so the screen reader still gets a spoken reply.
    screened = input_screen.screen(question)
    yield {"stage": "screen", "ok": screened.ok, "category": screened.category}
    if not screened.ok:
        yield {
            "stage": "verdict",
            "text": input_screen.decline_message(language),
            "question": "[withheld]",
            "law_text": "",
            "safe": True,
            "declined": True,
            "screen_category": screened.category,
        }
        return

    with tracer.start_as_current_span("law") as span:
        law = retriever.retrieve(question)
        span.set_attribute("varsity.law", law.law)
        span.set_attribute("varsity.law_title", law.title)
    yield {"stage": "law", "law": law.law, "title": law.title, "text": law.text}

    with tracer.start_as_current_span("granite") as span:
        answer = granite.answer_question(
            question=question,
            law=law.law,
            title=law.title,
            law_text=law.text,
            language=language,
        )
        model = getattr(getattr(granite, "config", None), "model_id", "granite")
        source = getattr(granite, "last_source", "granite")
        span.set_attribute("varsity.model", model)
        span.set_attribute("varsity.source", source)
        span.set_attribute("varsity.language", language)
    yield {"stage": "granite", "model": model, "source": source}

    with tracer.start_as_current_span("guardian") as span:
        verdict = guardian.check(answer, law_context=law.text)
        span.set_attribute("varsity.safe", verdict.safe)
        span.set_attribute("varsity.grounded", verdict.grounded)
        span.set_attribute("varsity.screen_reader_ok", verdict.screen_reader_ok)
        span.set_attribute("varsity.guardian_model", getattr(guardian, "model_id", "guardian"))
    yield {
        "stage": "guardian",
        "safe": verdict.safe,
        "cites_law": verdict.cites_law,
        "grounded": verdict.grounded,
        "screen_reader_ok": verdict.screen_reader_ok,
        "answer": verdict.model_answer,
    }

    panel = verification.verify(
        explanation=answer,
        cites_law=verdict.cites_law,
        grounded=verdict.grounded,
        screen_reader_ok=verdict.screen_reader_ok,
    )
    yield verification.verification_stage(panel)

    manifest = provenance.build_manifest(
        decision_id=f"ask: {question[:48]}",
        source="Fan question",
        law=law.law,
        law_title=law.title,
        model=model,
        grounded=verdict.grounded,
        verified=panel.verified,
        links=[provenance.link_from_law(law=law.law, law_title=law.title, law_text=law.text)],
        guardian_model=getattr(guardian, "model_id", None)
        or "ibm/granite-guardian-3-8b",
    )
    yield provenance.provenance_stage(manifest)
    yield citation_metrics.citation_metrics_stage(manifest.links)

    yield {
        "stage": "verdict",
        "text": answer,
        "question": question,
        "law": law.law,
        "law_title": law.title,
        "law_text": law.text,
        "safe": verdict.safe,
    }


def explain_offside_decision(frame: list[FreezeFramePlayer], **kwargs) -> PipelineResult:
    stages = {s["stage"]: s for s in explanation_stages(frame, **kwargs)}
    geo, law, guard, verdict = (
        stages["geometry"],
        stages["law"],
        stages["guardian"],
        stages["verdict"],
    )
    return PipelineResult(
        is_offside=geo["is_offside"],
        margin_meters=geo["margin_meters"],
        law=law["law"],
        law_title=law["title"],
        explanation=verdict["text"],
        safe=guard["safe"],
        cites_law=guard["cites_law"],
        grounded=guard["grounded"],
    )
