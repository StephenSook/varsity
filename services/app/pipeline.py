"""The VARSITY explanation pipeline: geometry -> Law retrieval -> Granite -> Guardian.

``explanation_stages`` is a generator that yields one dict per stage, so the SSE
endpoint can stream the pipeline unfolding (and the front end can render both the
spoken verdict and the per-stage trace). Clients are injectable for offline tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from app.decisions import get_decision
from app.geometry import FreezeFramePlayer, compute_offside
from app.llm.granite import GraniteClient
from app.llm.guardian import GuardianClient
from app.observability import tracer
from app.rag.retriever import LawRetriever
from app.signals import referee_signal
from app.uncertainty import quantify

OFFSIDE_QUERY = "offside attacker nearer the goal line than the second-last defender and the ball"


def _confidence(margin_meters: float) -> str:
    """How clear-cut the call is, grounded in the ~13 cm measurement-noise band (uncertainty)."""
    return quantify(margin_meters).band


def _uncertainty_fields(margin_meters: float) -> dict:
    """The 'VARSITY's Call' uncertainty payload shared by the geometry + verdict stages."""
    unc = quantify(margin_meters)
    return {
        "confidence": unc.band,
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

    sig = referee_signal(is_offside=geo.is_offside)
    yield {"stage": "signal", "text": sig["text"], "law": sig["law"]}

    with tracer.start_as_current_span("law") as span:
        law = retriever.retrieve(OFFSIDE_QUERY)
        span.set_attribute("varsity.law", law.law)
        span.set_attribute("varsity.law_title", law.title)
    yield {"stage": "law", "law": law.law, "title": law.title, "text": law.text}

    with tracer.start_as_current_span("granite") as span:
        explanation = granite.explain_offside(
            margin_meters=geo.margin_meters,
            is_offside=geo.is_offside,
            law_text=law.text,
            language=language,
        )
        model = getattr(getattr(granite, "config", None), "model_id", "granite")
        span.set_attribute("varsity.model", model)
        span.set_attribute("varsity.language", language)
    yield {"stage": "granite", "model": model}

    with tracer.start_as_current_span("guardian") as span:
        verdict = guardian.check(explanation, law_context=law.text)
        span.set_attribute("varsity.safe", verdict.safe)
        span.set_attribute("varsity.grounded", verdict.grounded)
        span.set_attribute("varsity.screen_reader_ok", verdict.screen_reader_ok)
    yield {
        "stage": "guardian",
        "safe": verdict.safe,
        "cites_law": verdict.cites_law,
        "grounded": verdict.grounded,
        "screen_reader_ok": verdict.screen_reader_ok,
        "answer": verdict.model_answer,
    }

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
        span.set_attribute("varsity.model", model)
        span.set_attribute("varsity.language", language)
    yield {"stage": "granite", "model": model}

    with tracer.start_as_current_span("guardian") as span:
        verdict = guardian.check(explanation, law_context=law.text)
        span.set_attribute("varsity.safe", verdict.safe)
        span.set_attribute("varsity.grounded", verdict.grounded)
        span.set_attribute("varsity.screen_reader_ok", verdict.screen_reader_ok)
    yield {
        "stage": "guardian",
        "safe": verdict.safe,
        "cites_law": verdict.cites_law,
        "grounded": verdict.grounded,
        "screen_reader_ok": verdict.screen_reader_ok,
        "answer": verdict.model_answer,
    }

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
        span.set_attribute("varsity.model", model)
        span.set_attribute("varsity.language", language)
    yield {"stage": "granite", "model": model}

    with tracer.start_as_current_span("guardian") as span:
        verdict = guardian.check(answer, law_context=law.text)
        span.set_attribute("varsity.safe", verdict.safe)
        span.set_attribute("varsity.grounded", verdict.grounded)
        span.set_attribute("varsity.screen_reader_ok", verdict.screen_reader_ok)
    yield {
        "stage": "guardian",
        "safe": verdict.safe,
        "cites_law": verdict.cites_law,
        "grounded": verdict.grounded,
        "screen_reader_ok": verdict.screen_reader_ok,
        "answer": verdict.model_answer,
    }

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
