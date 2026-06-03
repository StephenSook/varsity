"""The VARSITY explanation pipeline: geometry -> Law retrieval -> Granite -> Guardian.

``explanation_stages`` is a generator that yields one dict per stage, so the SSE
endpoint can stream the pipeline unfolding (and the front end can render both the
spoken verdict and the per-stage trace). Clients are injectable for offline tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from app.geometry import FreezeFramePlayer, compute_offside
from app.llm.granite import GraniteClient
from app.llm.guardian import GuardianClient
from app.observability import tracer
from app.rag.retriever import LawRetriever

OFFSIDE_QUERY = "offside attacker nearer the goal line than the second-last defender and the ball"


def _confidence(margin_meters: float) -> str:
    """How clear-cut the call is, from the geometry margin. Honest about marginal calls."""
    m = abs(margin_meters)
    if m >= 0.5:
        return "clear"
    if m >= 0.2:
        return "tight"
    return "very tight"


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
        "confidence": _confidence(geo.margin_meters),
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
        "confidence": _confidence(geo.margin_meters),
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
