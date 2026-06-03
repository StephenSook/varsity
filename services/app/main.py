"""VARSITY backend (FastAPI) with a Server-Sent Events explanation stream.

GET /stream/canned runs the deterministic canned StatsBomb-360 offside through the
full pipeline and streams each stage as an SSE event. The front end feeds the
final ``verdict`` event into its aria-live region and renders the stages as the
pipeline trace.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app import decisions, scenarios
from app.observability import setup_tracing
from app.pipeline import decision_stages, explanation_stages, question_stages
from app.rag.retriever import LawRetriever
from app.triggers.resolver import pick_transitional, resolve_live_var_events, reviewing_stage

app = FastAPI(title="VARSITY backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# Emit an OpenTelemetry span tree per request (HTTP span + nested pipeline stages).
setup_tracing(app)

_SENTINEL = object()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "varsity-backend"}


@app.get("/scenarios")
def list_scenarios() -> dict[str, list[dict]]:
    """The real World Cup 2022 freeze-frames the demo can play (offside/onside/tight).

    Each carries its byline + the geometry-computed expected verdict, so a judge can see
    the engine returns different real answers, not one fixed offside.
    """
    return {"scenarios": scenarios.scenarios_index()}


@app.get("/stream/canned")
async def stream_canned(
    language: str = "English", scenario: str = scenarios.DEFAULT_SCENARIO
) -> EventSourceResponse:
    frame = scenarios.load_frame(scenario)
    meta = scenarios.trigger_meta(scenario)

    async def event_gen():
        gen = explanation_stages(frame, language=language, trigger_meta=meta)
        while True:
            stage = await asyncio.to_thread(next, gen, _SENTINEL)
            if stage is _SENTINEL:
                break
            yield {"event": stage["stage"], "data": json.dumps(stage)}

    return EventSourceResponse(event_gen())


@app.get("/stream/live")
async def stream_live(
    language: str = "English", scenario: str = scenarios.DEFAULT_SCENARIO
) -> EventSourceResponse:
    """Live-trigger beat: emit the transitional 'VAR is reviewing' announcement, then
    the full explanation. Uses the deterministic replay floor so the demo never depends
    on a live match; real Sportmonks / API-Football events are used when available.
    """
    frame = scenarios.load_frame(scenario)
    meta = scenarios.trigger_meta(scenario)
    events, source = resolve_live_var_events()
    transitional = pick_transitional(events)

    async def event_gen():
        if transitional is not None:
            yield {
                "event": "reviewing",
                "data": json.dumps(reviewing_stage(transitional, source)),
            }
        gen = explanation_stages(frame, language=language, trigger_meta=meta)
        while True:
            stage = await asyncio.to_thread(next, gen, _SENTINEL)
            if stage is _SENTINEL:
                break
            yield {"event": stage["stage"], "data": json.dumps(stage)}

    return EventSourceResponse(event_gen())


_retriever: LawRetriever | None = None


def _law_retriever() -> LawRetriever:
    global _retriever
    if _retriever is None:
        _retriever = LawRetriever()
    return _retriever


@app.get("/law_clause")
def law_clause(q: str | None = None, law: str | None = None) -> dict:
    """Resolve a Laws-of-the-Game query (or an exact Law number) to the official IFAB clause
    text + its citation. This is the ``get_law_clause`` tool, exposed over REST so the existing
    Context Forge federation can wrap it as an MCP tool; it is how every spoken rule claim
    resolves to the official text. Read-only; never adjudicates. BM25 over the Docling-parsed
    corpus (no model call), so it is deterministic and fast."""
    retriever = _law_retriever()
    if law:
        chunk = next((c for c in retriever.chunks if c.law == law), None)
        if chunk is None:
            return {"found": False, "query": law}
    else:
        chunk = retriever.retrieve(
            (q or "offside").strip()[:300] or "offside", use_embeddings=False
        )
    return {
        "found": True,
        "citation_id": f"Law {chunk.law}",
        "law": chunk.law,
        "title": chunk.title,
        "text": chunk.text,
        "source": "IFAB Laws of the Game 2025/26",
    }


@app.get("/decisions")
def list_decisions() -> dict[str, list[dict]]:
    """The non-geometry VAR decisions the demo can explain (penalty, handball).

    Same RAG + Granite + Guardian engine as offside; clearly tiered ``illustrative``.
    """
    return {"decisions": decisions.decisions_index()}


@app.get("/stream/decision")
async def stream_decision(type: str, language: str = "English") -> EventSourceResponse:
    """Explain a non-geometry VAR decision (penalty, handball) end to end: the same
    rule-grounded pipeline as offside, with no geometry/offside-line stage."""

    async def event_gen():
        gen = decision_stages(type, language=language)
        while True:
            stage = await asyncio.to_thread(next, gen, _SENTINEL)
            if stage is _SENTINEL:
                break
            yield {"event": stage["stage"], "data": json.dumps(stage)}

    return EventSourceResponse(event_gen())


@app.get("/stream/ask")
async def stream_ask(q: str, language: str = "English") -> EventSourceResponse:
    """The rule oracle: answer a free-text fan question end to end, grounded in the Law
    the retriever returns, with Guardian checking the answer stays grounded."""
    question = q.strip()[:300]

    async def event_gen():
        gen = question_stages(question, language=language)
        while True:
            stage = await asyncio.to_thread(next, gen, _SENTINEL)
            if stage is _SENTINEL:
                break
            yield {"event": stage["stage"], "data": json.dumps(stage)}

    return EventSourceResponse(event_gen())
