"""VARSITY backend (FastAPI) with a Server-Sent Events explanation stream.

GET /stream/canned runs the deterministic canned StatsBomb-360 offside through the
full pipeline and streams each stage as an SSE event. The front end feeds the
final ``verdict`` event into its aria-live region and renders the stages as the
pipeline trace.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app import decisions, scenarios
from app import latency as latency_model
from app.calibration import calibration_payload
from app.observability import setup_tracing
from app.pipeline import decision_stages, explanation_stages, question_stages
from app.rag import corpus_signature
from app.rag.retriever import CORPUS, SIGNATURE, LawRetriever
from app.ratelimit import rate_limit
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
_log = logging.getLogger("varsity")


async def _sse_events(gen):
    """Drive a stage generator to named SSE events. A last-resort boundary: if a stage raises
    unexpectedly, emit a terminal 'stream_error' event so the client can announce a grounded
    failure rather than the connection dropping with no signal, then stop. LLM stages already
    self-degrade; this guards the deterministic stages so the stream never dies silently."""
    try:
        while True:
            stage = await asyncio.to_thread(next, gen, _SENTINEL)
            if stage is _SENTINEL:
                break
            yield {"event": stage["stage"], "data": json.dumps(stage)}
    except Exception:  # noqa: BLE001 - boundary so one bad stage never kills the stream silently
        _log.exception("SSE stage generator failed")
        yield {
            "event": "stream_error",
            "data": json.dumps({"stage": "stream_error", "message": "stream failed"}),
        }

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


@app.get("/stream/canned", dependencies=[Depends(rate_limit)])
async def stream_canned(
    language: str = "English", scenario: str = scenarios.DEFAULT_SCENARIO
) -> EventSourceResponse:
    frame = scenarios.load_frame(scenario)
    meta = scenarios.trigger_meta(scenario)
    gen = explanation_stages(frame, language=language, trigger_meta=meta)
    return EventSourceResponse(_sse_events(gen))


@app.get("/stream/live", dependencies=[Depends(rate_limit)])
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
        try:
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
        except Exception:  # noqa: BLE001 - the reviewing beat is a flourish, never load-bearing
            _log.exception("live reviewing beat failed; proceeding to the explanation")
            warm = None
        prewarmed_law = warm.law if warm is not None else None
        gen = explanation_stages(
            frame, language=language, trigger_meta=meta, prewarmed_law=prewarmed_law
        )
        async for ev in _sse_events(gen):
            yield ev

    return EventSourceResponse(event_gen())


@app.get("/latency")
def latency(elapsed_s: float | None = None) -> dict:
    """The honest 'first in the room' latency framing: the VERIFIED broadcast-delay
    figures (Phenix field-of-play studies), the trigger -> spoken-verdict budget, and -
    with ``?elapsed_s=`` - the calibrated lead for a specific run. The live trigger is
    never load-bearing; the canned StatsBomb path is the floor."""
    return latency_model.payload(elapsed_s)


@app.get("/challenge_fit")
def challenge_fit() -> dict:
    """Why VARSITY fits the challenge, as primary-sourced facts a judge can check: the WHO scale of
    vision impairment, the FIFA scale of the 2026 World Cup it serves during, and the honest
    2022->2026 method transfer. Each figure carries the page it was verified against."""
    from app import challenge_fit as cf

    return cf.payload()


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


# Cache the live-feed snapshot so a judge clicking "what is live now" repeatedly does not burn the
# free-tier daily quota; on-demand only, no auto-polling. (single-instance backend, in-process.)
_LIVE_CACHE: dict = {"t": 0.0, "data": None}
_LIVE_TTL_S = 120.0


@app.get("/live/now")
def live_now() -> dict:
    """What is live right now from the REAL API-Football feed: the matches in play, their minute,
    and any VAR review detail. Proves VARSITY is wired to a live feed, not just canned replay. A VAR
    review in a covered match is explainable live through the same pipeline; the precise offside
    margin still uses the known frame, because no public live feed exposes the player-tracking data
    a margin needs. Honest when no key is configured (the canned StatsBomb path is the floor)."""
    now = time.time()
    if _LIVE_CACHE["data"] is not None and now - _LIVE_CACHE["t"] < _LIVE_TTL_S:
        return {**_LIVE_CACHE["data"], "cached": True}
    _sportmonks, apifootball = live_clients()
    if apifootball is None:
        return {
            "configured": False,
            "feed_ok": False,
            "fixtures": [],
            "note": "No live-feed key configured; the canned StatsBomb replay is the floor.",
        }
    try:
        fixtures = apifootball.live_fixtures()
    except Exception:
        # A quota / auth / network failure must NOT masquerade as a quiet window. Report it
        # honestly and do NOT cache it, so a recovered feed is re-queried on the next click.
        _log.warning("live_now feed call failed", exc_info=True)
        return {
            "configured": True,
            "feed_ok": False,
            "fixtures": [],
            "live_count": 0,
            "note": (
                "Live feed temporarily unavailable (quota, auth, or network); the canned "
                "StatsBomb replay remains the floor."
            ),
        }
    data = {
        "configured": True,
        "feed_ok": True,
        "source": "api-football",
        "live_count": len(fixtures),
        "fixtures": fixtures[:20],
        "var_events": [f for f in fixtures if f.get("var_events")],
        "note": (
            "Live fixtures from the real feed. A VAR review in a covered match is explained live; "
            "the offside margin uses the known frame (no public live feed exposes tracking data)."
        ),
        "cached": False,
    }
    _LIVE_CACHE["t"] = now
    _LIVE_CACHE["data"] = data
    return data


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


@app.get("/rag_eval")
def rag_eval() -> dict:
    """Retrieval-quality receipt for the IFAB-Law RAG: Hit@k + MRR over a 20-question golden set.
    The committed numbers are the BM25 OFFLINE floor (the deterministic, dependency-free retriever
    that CI runs without a watsonx key); the LIVE product retrieves with IBM Granite embeddings +
    FAISS. The embedding model id and the two retriever paths are returned as SEPARATE fields so the
    floor numbers are never mis-attributed to the embedding model (a faithfulness discipline)."""
    from pathlib import Path

    from app.rag.retriever import GRANITE_EMBED_MODEL

    path = Path(__file__).resolve().parent.parent / "evals" / "scores.json"
    scores = json.loads(path.read_text())
    return {
        "scores": scores,
        "scored_retriever": scores.get("path"),  # what produced these numbers: "bm25 (offline)"
        "online_retriever": "IBM Granite embeddings + FAISS",
        "embedding_model": GRANITE_EMBED_MODEL,
        "golden_questions": scores.get("n"),
        "note": (
            "Hit@k / MRR over a 20-question golden set. The numbers are the BM25 offline floor "
            "(the deterministic retriever CI runs, no watsonx key); the live product retrieves "
            "with IBM Granite embeddings + FAISS. Stated apart so the floor is not mis-credited."
        ),
    }


@app.get("/trace")
def otel_trace() -> dict:
    """Run one canned VAR explanation under the OpenTelemetry instrumentation and return the REAL
    span tree (the same spans setup_tracing prints to stdout) so a judge SEES the distributed trace
    of one decision live in the browser, with per-stage durations. OTel is otherwise stdout-only and
    invisible to a judge; this makes the instrumentation a verifiable IBM-stack artifact."""
    from app.observability import captured_span_tree, clear_captured_spans

    clear_captured_spans()
    frame = scenarios.load_frame(scenarios.DEFAULT_SCENARIO)
    stages_run = [s["stage"] for s in explanation_stages(frame)]
    spans = captured_span_tree()
    return {
        "service": "varsity-backend",
        "stages_run": stages_run,
        "spans": spans,
        "span_count": len(spans),
        "note": (
            "Real OpenTelemetry spans (the same tree setup_tracing prints to stdout), captured "
            "in-memory for this run: the pipeline stages instrumented in app/pipeline.py."
        ),
    }


@app.get("/models")
def models() -> dict:
    """The IBM Granite-family model registry: every IBM model VARSITY runs, named and resolved from
    the live config (env overrides honored), in one place - the single-glance 'best use of IBM
    technology' artifact. Returns only whether the watsonx key is configured, never the key."""
    import os

    from app.llm import _watsonx
    from app.llm.granite import GraniteConfig
    from app.llm.guardian import GuardianClient
    from app.llm.vision import vision_model_id
    from app.rag.retriever import GRANITE_EMBED_MODEL

    reasoning = GraniteConfig.from_env().model_id
    safety = GuardianClient().model_id
    return {
        "models": [
            {"role": "reasoning", "model_id": reasoning, "via": "watsonx text"},
            {"role": "safety", "model_id": safety, "via": "watsonx chat risk head"},
            {"role": "embeddings", "model_id": GRANITE_EMBED_MODEL, "via": "watsonx embeddings"},
            {"role": "vision", "model_id": vision_model_id(), "via": "watsonx image (build-time)"},
        ],
        "watsonx_region": _watsonx._base_url(),
        "watsonx_configured": bool(os.environ.get("WATSONX_API_KEY")),
        "note": "Every IBM Granite model VARSITY uses, resolved live; the key is never sent.",
    }


@app.get("/uncertainty")
def uncertainty(margin_m: float = 5.69, is_offside: bool | None = None) -> dict:
    """The GUM uncertainty budget for an offside margin: the honest broadcast-data expanded
    uncertainty + coverage interval (BIPM JCGM 100:2008, k=2 ~ 95%), the Bayesian credible
    interval, the Shannon entropy of the call in bits, a Monte-Carlo cross-check (JCGM 101:2008),
    and the two-regime comparison (optical-tracking-equivalent vs broadcast-annotation). It
    DESCRIBES the precision of the received decision's geometry; it never adjudicates."""
    from app import gum

    # Derive the verdict from the margin sign (geometry convention: positive = ahead of the binding
    # Law-11 reference = offside), matching the live pipeline (which passes geo.is_offside), so the
    # spoken line never says "onside" for a positive (offside) margin. An explicit param overrides.
    verdict_offside = is_offside if is_offside is not None else margin_m > 0
    return gum.payload(margin_m, is_offside=verdict_offside, extended=True)


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


@app.get("/stream/decision", dependencies=[Depends(rate_limit)])
async def stream_decision(type: str, language: str = "English") -> EventSourceResponse:
    """Explain a non-geometry VAR decision (penalty, handball) end to end: the same
    rule-grounded pipeline as offside, with no geometry/offside-line stage."""

    return EventSourceResponse(_sse_events(decision_stages(type, language=language)))


@app.get("/stream/ask", dependencies=[Depends(rate_limit)])
async def stream_ask(q: str, language: str = "English") -> EventSourceResponse:
    """The rule oracle: answer a free-text fan question end to end, grounded in the Law
    the retriever returns, with Guardian checking the answer stays grounded."""
    question = q.strip()[:300]
    return EventSourceResponse(_sse_events(question_stages(question, language=language)))
