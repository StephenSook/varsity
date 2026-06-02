#!/usr/bin/env bash
# Launch VARSITY's three federated backends for Context Forge registration:
#   ifab-rag MCP        (SSE :8001)
#   match-geometry MCP  (SSE :8002)
#   A2A narrator        (JSON-RPC :9000)
# Then, in another shell: `python -m scripts.register_federation` (gateway must be up).
# Ctrl-C stops all three.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
export PYTHONPATH="$ROOT/services"

trap 'kill 0' EXIT INT TERM

"$PY" -m app.mcp_servers.ifab_rag &
"$PY" -m app.mcp_servers.geometry_server &
"$PY" -m app.a2a_agent.narrator &

echo "ifab-rag :8001 | match-geometry :8002 | narrator :9000  (Ctrl-C to stop)"
wait
