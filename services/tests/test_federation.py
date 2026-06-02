from app.federation import federation_targets


def test_federation_targets_default() -> None:
    targets = federation_targets()
    assert [t.name for t in targets] == ["ifab-rag", "match-geometry", "narrator"]
    assert {t.path for t in targets} == {"/gateways", "/a2a"}

    rag = next(t for t in targets if t.name == "ifab-rag")
    assert rag.path == "/gateways"
    assert rag.payload["url"].endswith(":8001/sse")
    assert rag.payload["transport"] == "SSE"
    assert "host.docker.internal" in rag.payload["url"]

    narr = next(t for t in targets if t.name == "narrator")
    assert narr.path == "/a2a"
    # A2A registration nests the agent body under "agent" (confirmed vs live gateway).
    assert narr.payload["agent"]["endpoint_url"].endswith(":9000")


def test_federation_targets_custom_host() -> None:
    targets = federation_targets(backend_host="localhost")
    for t in targets:
        body = t.payload.get("agent", t.payload)
        endpoint = body.get("url") or body["endpoint_url"]
        assert "localhost" in endpoint
