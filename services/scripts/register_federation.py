"""CLI: register VARSITY's backends with the Context Forge gateway.

Prereqs: the gateway is up and the three backends are running
(``services/scripts/run_federation.sh``). The Docker GA image hangs at startup on
arm64; the working path is the PyPI gateway on the host (see ``docs/federation.md``).

Env:
    CONTEXT_FORGE_URL          gateway base URL (default http://localhost:4444)
    CONTEXT_FORGE_TOKEN        bearer token (mcpgateway.utils.create_jwt_token)
    CONTEXT_FORGE_BACKEND_HOST host the gateway reaches the backends on
                               (default host.docker.internal; use localhost for a
                               host-run gateway with SSRF_ALLOW_LOCALHOST=true)

Usage (from services/, with PYTHONPATH=.):
    python -m scripts.register_federation            # register all 4 backends
    python -m scripts.register_federation --dry-run  # print payloads only, no POST
"""

from __future__ import annotations

import json
import os
import sys

from app.federation import DEFAULT_GATEWAY, federation_targets, register_all


def main(argv: list[str]) -> int:
    backend_host = os.environ.get("CONTEXT_FORGE_BACKEND_HOST")
    targets = federation_targets(backend_host) if backend_host else federation_targets()
    if "--dry-run" in argv:
        for t in targets:
            print(f"POST {t.path}  {json.dumps(t.payload)}")
        return 0
    base = os.environ.get("CONTEXT_FORGE_URL", DEFAULT_GATEWAY)
    token = os.environ.get("CONTEXT_FORGE_TOKEN")
    if not token:
        print("CONTEXT_FORGE_TOKEN not set (see docs/federation.md).", file=sys.stderr)
        return 1
    print(f"Registering backends with {base} ...")
    for name, code in register_all(base, token, targets):
        flag = "ok" if code < 400 else "FAILED"
        print(f"  {name}: HTTP {code} {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
