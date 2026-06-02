"""VARSITY backend (FastAPI) with a Server-Sent Events explanation stream.

GET /stream/canned runs the deterministic canned StatsBomb-360 offside through the
full pipeline and streams each stage as an SSE event. The front end feeds the
final ``verdict`` event into its aria-live region and renders the stages as the
pipeline trace.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.geometry import FreezeFramePlayer
from app.pipeline import explanation_stages
from app.triggers.resolver import pick_transitional, resolve_live_var_events, reviewing_stage

app = FastAPI(title="VARSITY backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FIXTURE = Path(__file__).resolve().parent.parent / "tests/fixtures/wc2022_offside_frame.json"
_SENTINEL = object()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "varsity-backend"}


def _canned_frame() -> list[FreezeFramePlayer]:
    data = json.loads(FIXTURE.read_text())
    return [FreezeFramePlayer(**p) for p in data["players"]]


@app.get("/stream/canned")
async def stream_canned(language: str = "English") -> EventSourceResponse:
    frame = _canned_frame()

    async def event_gen():
        gen = explanation_stages(frame, language=language)
        while True:
            stage = await asyncio.to_thread(next, gen, _SENTINEL)
            if stage is _SENTINEL:
                break
            yield {"event": stage["stage"], "data": json.dumps(stage)}

    return EventSourceResponse(event_gen())


@app.get("/stream/live")
async def stream_live(language: str = "English") -> EventSourceResponse:
    """Live-trigger beat: emit the transitional 'VAR is reviewing' announcement, then
    the full explanation. Uses the deterministic replay floor so the demo never depends
    on a live match; real Sportmonks / API-Football events are used when available.
    """
    frame = _canned_frame()
    events, source = resolve_live_var_events()
    transitional = pick_transitional(events)

    async def event_gen():
        if transitional is not None:
            yield {
                "event": "reviewing",
                "data": json.dumps(reviewing_stage(transitional, source)),
            }
        gen = explanation_stages(frame, language=language)
        while True:
            stage = await asyncio.to_thread(next, gen, _SENTINEL)
            if stage is _SENTINEL:
                break
            yield {"event": stage["stage"], "data": json.dumps(stage)}

    return EventSourceResponse(event_gen())
