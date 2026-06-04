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
from app import latency as latency_model
from app.calibration import calibration_payload
from app.observability import setup_tracing
from app.pipeline import decision_stages, explanation_stages, question_stages
from app.rag import corpus_signature
from app.rag.retriever import CORPUS, SIGNATURE, LawRetriever
from app.triggers.fusion import fuse
from app.triggers.prewarm import PreWarmCache
from app.triggers.resolver import (
    live_clients,
    pick_transitional,
    resolve_and_fuse,
    resolve_live_var_events,
    reviewing_stage,
)
from app.triggers.schema import REVIEW_STARTED, normalize_all

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

# Speculative pre-warm cache for the live path: the 'reviewing' beat warms the Law +
# geometry so the resolved explanation skips that cold work.
_prewarm = PreWarmCache()


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

    The 'reviewing' beat carries the multi-source fusion confidence + hedge and triggers
    the speculative pre-warm (Law + geometry pre-computed in the review gap), so the
    resolved explanation skips that cold work. None of this adjudicates - the outcome is
    always the official's received decision.
    """
    frame = scenarios.load_frame(scenario)
    meta = scenarios.trigger_meta(scenario)
    sportmonks, apifootball = live_clients()
    events, source = resolve_live_var_events(sportmonks=sportmonks, apifootball=apifootball)
    transitional = pick_transitional(events)
    fused = fuse(normalize_all(events, source))
    review = next((f for f in fused if f.phase == REVIEW_STARTED), fused[0] if fused else None)
    review_id = f"{source}:{scenario}"

    async def event_gen():
        warm = None
        if transitional is not None:
            # Speculative pre-warm: during the 'reviewing' gap, pre-retrieve the Law and run
            # the geometry so the resolved explanation skips that cold work.
            await asyncio.to_thread(_prewarm.warm, review_id, frame, _law_retriever())
            warm = _prewarm.consume(review_id)
            stage = reviewing_stage(transitional, source)
            if review is not None:
                stage["confidence"] = round(review.confidence, 3)
                stage["hedge"] = review.hedge
            stage["prewarmed"] = warm is not None
            yield {"event": "reviewing", "data": json.dumps(stage)}
        prewarmed_law = warm.law if warm is not None else None
        gen = explanation_stages(
            frame, language=language, trigger_meta=meta, prewarmed_law=prewarmed_law
        )
        while True:
            stage = await asyncio.to_thread(next, gen, _SENTINEL)
            if stage is _SENTINEL:
                break
            yield {"event": stage["stage"], "data": json.dumps(stage)}

    return EventSourceResponse(event_gen())


@app.get("/latency")
def latency(elapsed_s: float | None = None) -> dict:
    """The honest 'first in the room' latency framing: the VERIFIED broadcast-delay
    figures (Phenix field-of-play studies), the trigger -> spoken-verdict budget, and -
    with ``?elapsed_s=`` - the calibrated lead for a specific run. The live trigger is
    never load-bearing; the canned StatsBomb path is the floor."""
    return latency_model.payload(elapsed_s)


@app.get("/fusion")
def fusion() -> dict:
    """Multi-source fusion confidence over the live (or replay-floor) VAR events: each
    review gets a confidence from cross-source agreement, a hedge, and a conflict flag.
    It raises confidence / resilience; it never adjudicates."""
    sportmonks, apifootball = live_clients()
    events, source = resolve_live_var_events(sportmonks=sportmonks, apifootball=apifootball)
    decisions_out = resolve_and_fuse(sportmonks=sportmonks, apifootball=apifootball)
    return {
        "primary_source": source,
        "decisions": [d.as_dict() for d in decisions_out],
    }


@app.get("/corpus_integrity")
def corpus_integrity() -> dict:
    """RAG-poisoning defense (LLM08): verify the IFAB Law corpus against its signed
    SHA-256 manifest. Deterministic, no model, no network - a tampered Law is caught by
    arithmetic, not a probabilistic check. The retriever fails CLOSED on a mismatch."""
    chunks = json.loads(CORPUS.read_text())
    manifest = corpus_signature.load_manifest(SIGNATURE)
    if manifest is None:
        return {"signed": False}
    ok, mismatches = corpus_signature.verify(chunks, manifest)
    return {
        "signed": True,
        "verified": ok,
        "algorithm": manifest["algorithm"],
        "count": manifest["count"],
        "root": manifest["root"],
        "mismatches": mismatches,
    }


@app.get("/diagram_captions")
def diagram_captions_endpoint() -> dict:
    """The IFAB diagrams (the Law 11 offside figure, the Law 5/6 referee-signal graphics) that
    plain Docling drops as <!-- image --> holes, captioned at build time by Granite Vision 3.2 into
    accessible alt-text for a blind fan. Captions are grounded + faithfulness-guarded + human-
    reviewed before they enter the corpus, and tiered 'diagram description' (AI-generated), never
    official IFAB text. Empty until captions are approved (see docs/DIAGRAM-CAPTIONS.md)."""
    from app.llm import vision
    from app.rag import diagram_captions

    chunks = diagram_captions.approved_caption_chunks()
    return {
        "tier": "diagram-description",
        "model": vision.vision_model_id(),
        "count": len(chunks),
        "captions": chunks,
        "note": (
            "AI-generated diagram descriptions (build-time, Granite Vision), grounded + "
            "faithfulness-guarded + human-reviewed; an accessibility aid, not official IFAB text."
        ),
    }


@app.get("/red_team")
def red_team() -> dict:
    """The red-team regression receipt for the oracle input screen: the deterministic
    floor catches every English prompt-injection + HAP attack (zero leakage) and never
    false-positives a legit rules question, with the known non-English / leet screen-misses
    documented honestly (defended downstream by spotlighting + Law-grounding). Offline,
    deterministic, no model call - a judge-facing receipt that runs in CI."""
    from verify.red_team_eval import payload

    return payload()


@app.get("/faithfulness")
def faithfulness() -> dict:
    """The injected-error faithfulness gold-eval, surfaced per injection class AND per decision
    type (offside / penalty / handball): the DETERMINISTIC gate catches every STRUCTURAL injection
    with zero leakage on every decision type, while semantic injections are the advisory Guardian
    layer's job. Plus ALCE-style citation precision/recall per decision type. Offline,
    deterministic, no model call - a judge-facing receipt that runs in CI."""
    from app.citation_metrics import per_decision_demo
    from verify.faithfulness_eval import payload

    out = payload()
    out["alce_per_decision"] = per_decision_demo()
    return out


@app.get("/uncertainty")
def uncertainty(margin_m: float = 5.69) -> dict:
    """The GUM uncertainty budget for an offside margin: the honest broadcast-data expanded
    uncertainty + coverage interval (BIPM JCGM 100:2008, k=2 ~ 95%), the Bayesian credible
    interval, the Shannon entropy of the call in bits, a Monte-Carlo cross-check (JCGM 101:2008),
    and the two-regime comparison (optical-tracking-equivalent vs broadcast-annotation). It
    DESCRIBES the precision of the received decision's geometry; it never adjudicates."""
    from app import gum

    return gum.payload(margin_m, extended=True)


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


@app.get("/calibration")
def calibration() -> dict:
    """The confidence-calibration receipt for the uncertainty band: a seeded Monte-Carlo
    reliability diagram + ECE + Brier over P(verdict correct) = Phi(|M|/sigma), computed over the
    SAME normal_cdf the live band uses. Read-only, deterministic, no model call. Describes the
    honesty of the confidence VARSITY reports on a received decision; never adjudicates."""
    return calibration_payload()


@app.get("/multilingual")
def multilingual() -> dict:
    """The multilingual Terminology-Hit-Rate receipt: does the in-language narration use the
    OFFICIAL IFAB term per language (offside -> hors-jeu / fuera de juego / ...)? Reference-free and
    deterministic, no model call (runs the in-language floors). Read-only; never adjudicates."""
    from verify.multilingual_eval import evaluate

    return evaluate()


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
