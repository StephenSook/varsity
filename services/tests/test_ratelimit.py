from fastapi.testclient import TestClient

from app import ratelimit
from app.main import app


def test_paid_stream_is_rate_limited_per_ip(monkeypatch) -> None:
    # The paid /stream/* routes each trigger watsonx calls; a public unauthenticated API must
    # cap an abuser. With a low limit, the (N+1)th request from one IP gets 429 (refused before
    # the pipeline runs), not another paid model call.
    monkeypatch.setattr(ratelimit, "_MAX_PER_WINDOW", 3)
    ratelimit.reset()
    client = TestClient(app)
    codes = [client.get("/stream/canned?scenario=offside").status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200], codes
    assert codes[3] == 429, codes


def test_rate_limit_is_per_endpoint_independent_of_query(monkeypatch) -> None:
    # The limit is per IP across the paid streams; the oracle path is covered too.
    monkeypatch.setattr(ratelimit, "_MAX_PER_WINDOW", 2)
    ratelimit.reset()
    client = TestClient(app)
    assert client.get("/stream/ask?q=why%20offside").status_code == 200
    assert client.get("/stream/decision?type=penalty").status_code == 200
    assert client.get("/stream/canned?scenario=onside").status_code == 429
