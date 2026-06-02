"""Context Forge federation: register VARSITY's backends behind the gateway.

Four backends fan out behind the Context Forge gateway (the `/admin` observability
trace over this fan-out is the hero Technical-Execution artifact):

1. ifab-rag MCP server      (retrieve_law,            SSE :8001)
2. match-geometry MCP server (compute_offside_margin, SSE :8002)
3. A2A narrator agent        (a2a_narrator,           JSON-RPC :9000)
4. Granite coordinator       (watsonx, on top of the above)

The gateway runs in Docker, so host-run backends are reached via
``host.docker.internal``. Endpoints/field names follow ``infra/README.md``; they
are confirmed against the live gateway's OpenAPI when the container is up.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_GATEWAY = "http://localhost:4444"
DEFAULT_BACKEND_HOST = "host.docker.internal"


@dataclass(frozen=True)
class Registration:
    kind: str  # "gateway" (MCP server) | "a2a" (A2A agent)
    path: str  # gateway API path
    payload: dict


def federation_targets(backend_host: str = DEFAULT_BACKEND_HOST) -> list[Registration]:
    """The MCP servers + A2A narrator registered behind the Context Forge gateway."""
    return [
        Registration(
            "gateway", "/gateways",
            {"name": "ifab-rag", "url": f"http://{backend_host}:8001/sse"},
        ),
        Registration(
            "gateway", "/gateways",
            {"name": "match-geometry", "url": f"http://{backend_host}:8002/sse"},
        ),
        Registration(
            "a2a", "/a2a",
            {"name": "narrator", "endpoint_url": f"http://{backend_host}:9000"},
        ),
    ]


def register_all(
    base_url: str, token: str, targets: list[Registration] | None = None
) -> list[tuple[str, int]]:
    """POST each registration to the gateway; return (name, status_code) per target."""
    import httpx

    targets = targets or federation_targets()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    results: list[tuple[str, int]] = []
    with httpx.Client(base_url=base_url, timeout=30) as client:
        for t in targets:
            resp = client.post(t.path, json=t.payload, headers=headers)
            results.append((t.payload["name"], resp.status_code))
    return results
