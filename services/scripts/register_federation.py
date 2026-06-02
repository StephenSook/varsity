"""CLI: register VARSITY's backends with the Context Forge gateway.

Prereqs: the gateway is up (``cd infra && docker compose up -d``) and the three
backends are running (``services/scripts/run_federation.sh``).

Env:
    CONTEXT_FORGE_URL    gateway base URL (default http://localhost:4444)
    CONTEXT_FORGE_TOKEN  bearer token (see infra/README.md -> create_jwt_token)

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
    if "--dry-run" in argv:
        for t in federation_targets():
            print(f"POST {t.path}  {json.dumps(t.payload)}")
        return 0
    base = os.environ.get("CONTEXT_FORGE_URL", DEFAULT_GATEWAY)
    token = os.environ.get("CONTEXT_FORGE_TOKEN")
    if not token:
        print("CONTEXT_FORGE_TOKEN not set (see infra/README.md).", file=sys.stderr)
        return 1
    print(f"Registering backends with {base} ...")
    for name, code in register_all(base, token):
        flag = "ok" if code < 400 else "FAILED"
        print(f"  {name}: HTTP {code} {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
