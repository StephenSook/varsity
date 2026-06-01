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
from app.rag.retriever import LawRetriever

OFFSIDE_QUERY = "offside attacker nearer the goal line than the second-last defender and the ball"


@dataclass
class PipelineResult:
    is_offside: bool
    margin_meters: float
    law: str
    law_title: str
    explanation: str
    safe: bool
    cites_law: bool


def explanation_stages(
    frame: list[FreezeFramePlayer],
    *,
    language: str = "English",
    retriever: LawRetriever | None = None,
    granite: object | None = None,
    guardian: object | None = None,
) -> Iterator[dict]:
    retriever = retriever or LawRetriever()
    granite = granite or GraniteClient()
    guardian = guardian or GuardianClient()

    yield {"stage": "trigger", "source": "StatsBomb 360 (canned)"}

    geo = compute_offside(frame)
    yield {"stage": "geometry", "margin_meters": geo.margin_meters, "is_offside": geo.is_offside}

    law = retriever.retrieve(OFFSIDE_QUERY)
    yield {"stage": "law", "law": law.law, "title": law.title}

    explanation = granite.explain_offside(
        margin_meters=geo.margin_meters,
        is_offside=geo.is_offside,
        law_text=law.text,
        language=language,
    )
    model = getattr(getattr(granite, "config", None), "model_id", "granite")
    yield {"stage": "granite", "model": model}

    verdict = guardian.check(explanation)
    yield {
        "stage": "guardian",
        "safe": verdict.safe,
        "cites_law": verdict.cites_law,
        "answer": verdict.model_answer,
    }

    yield {
        "stage": "verdict",
        "text": explanation,
        "is_offside": geo.is_offside,
        "law": law.law,
        "margin_meters": geo.margin_meters,
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
    )
