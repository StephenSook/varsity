"""Per-IP rate limit for the paid streaming endpoints.

The ``/stream/*`` routes each trigger paid watsonx calls (Granite + Guardian). The API is
public and unauthenticated, so without a cap an abuser could spam them to burn the watsonx
quota and saturate the single Render worker. This bounds requests per client IP in a 60-second
sliding window.

It is deliberately generous: a human judge, even several behind one shared NAT, never
approaches the limit, while a scripted flood is cut off with 429. Dependency-free; the single
Render process + the asyncio single-threaded event loop mean a plain dict needs no lock. The
deterministic Law-citing floor still answers if watsonx is ever exhausted, so this is
defense-in-depth, never the only guard.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_WINDOW_S = 60.0
_MAX_PER_WINDOW = int(os.getenv("VARSITY_STREAM_RATE_LIMIT", "60"))
_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Render/Vercel sit behind a proxy, so the first X-Forwarded-For hop is the real client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request) -> None:
    """FastAPI dependency: raise 429 if this IP exceeded the window budget on a paid stream."""
    now = time.monotonic()
    q = _hits[_client_ip(request)]
    cutoff = now - _WINDOW_S
    while q and q[0] < cutoff:
        q.popleft()
    if len(q) >= _MAX_PER_WINDOW:
        retry = max(1, int(_WINDOW_S - (now - q[0])))
        raise HTTPException(
            status_code=429,
            detail="Too many requests; please slow down.",
            headers={"Retry-After": str(retry)},
        )
    q.append(now)


def reset() -> None:
    """Clear all counters (used by tests for per-test isolation)."""
    _hits.clear()
