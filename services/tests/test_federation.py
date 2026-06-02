from app.federation import federation_targets


def test_federation_targets_default() -> None:
    targets = federation_targets()
    names = [t.payload["name"] for t in targets]
    assert names == ["ifab-rag", "match-geometry", "narrator"]
    assert {t.kind for t in targets} == {"gateway", "a2a"}

    rag = next(t for t in targets if t.payload["name"] == "ifab-rag")
    assert rag.path == "/gateways"
    assert rag.payload["url"].endswith(":8001/sse")
    assert "host.docker.internal" in rag.payload["url"]

    narr = next(t for t in targets if t.payload["name"] == "narrator")
    assert narr.path == "/a2a"
    assert narr.payload["endpoint_url"].endswith(":9000")


def test_federation_targets_custom_host() -> None:
    targets = federation_targets(backend_host="localhost")
    for t in targets:
        endpoint = t.payload.get("url") or t.payload["endpoint_url"]
        assert "localhost" in endpoint
