"""HTTP-layer coverage for the /stream/* SSE routes.

The generators' content is unit-tested in test_pipeline, but the SSE wrapper itself (the sentinel
break-loop, the per-stage json.dumps serialization, and the event:/data: framing) is the only
channel that carries the spoken verdict to a blind fan, so it gets its own contract test here.
"""

import json

from fastapi.testclient import TestClient

from app.main import app


def _collect(path: str) -> list[tuple[str, dict]]:
    client = TestClient(app)
    out: list[tuple[str, dict]] = []
    with client.stream("GET", path) as r:
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        assert r.headers["content-type"].startswith("text/event-stream")
        name = ""
        for line in r.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                out.append((name, json.loads(line.split(":", 1)[1])))
    return out


def test_stream_canned_terminates_with_a_verdict_carrying_the_spoken_fields() -> None:
    events = _collect("/stream/canned?scenario=offside")
    names = [n for n, _ in events]
    assert "verdict" in names, names
    verdict = next(d for n, d in events if n == "verdict")
    # the exact fields the verdict handler reads and speaks to the blind fan
    assert {"text", "is_offside", "margin_meters"} <= verdict.keys()
    assert verdict["is_offside"] is True
    # every stage's data serialized to a JSON object (the framing never emits a non-JSON value)
    assert all(isinstance(d, dict) for _, d in events)
    assert "stream_error" not in names


def test_stream_decision_penalty_serializes_and_ends_in_a_verdict() -> None:
    events = _collect("/stream/decision?type=penalty")
    names = [n for n, _ in events]
    assert "verdict" in names, names
    assert all(isinstance(d, dict) for _, d in events)
    assert "stream_error" not in names


def test_stream_ask_serializes_and_ends_in_a_verdict() -> None:
    events = _collect("/stream/ask?q=why%20was%20that%20offside")
    names = [n for n, _ in events]
    assert "verdict" in names, names
    assert all(isinstance(d, dict) for _, d in events)
    assert "stream_error" not in names
