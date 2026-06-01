"""VARSITY backend (FastAPI).

Phase 0 skeleton: a health check plus a placeholder for the Server-Sent Events
stream that will push rule-grounded VAR explanations to the front-end ARIA live
region in Phase 1+.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VARSITY backend", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "varsity-backend"}
