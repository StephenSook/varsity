# Infrastructure

## IBM Context Forge MCP gateway

The gateway federates VARSITY's backends (IFAB-Laws RAG MCP server, match-data /
geometry MCP server, the A2A narrator agent) and a Granite coordinator, and
renders the `/admin` observability trace that is the hero technical artifact.

### Run it

Requires the Docker daemon running (start Docker Desktop).

```bash
# from infra/
docker compose up -d
docker compose logs -f gateway
```

Open http://localhost:4444/admin and log in with `PLATFORM_ADMIN_EMAIL` /
`PLATFORM_ADMIN_PASSWORD` (defaults `admin@example.com` / `changeme`; override in
the repo `.env`).

### Generate a bearer token

```bash
docker run --rm -it ghcr.io/ibm/mcp-context-forge:1.0.2 \
  python3 -m mcpgateway.utils.create_jwt_token \
  --username admin@example.com --exp 10080 --secret "$CONTEXT_FORGE_JWT_SECRET"
```

### Register the backends (federation)

Automated (registers all 4 backends at once; see `docs/federation.md` for the
full bring-up and the sequence diagram):

```bash
services/scripts/run_federation.sh   # launch ifab-rag :8001, match-geometry :8002, narrator :9000
# then, with the gateway up and a token in CONTEXT_FORGE_TOKEN:
cd services && PYTHONPATH=. python -m scripts.register_federation
#   preview without a gateway:  python -m scripts.register_federation --dry-run
```

Manual equivalent:

```bash
# an MCP server
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"ifab-rag","url":"http://host.docker.internal:8001/sse"}' \
  http://localhost:4444/gateways

# an A2A agent (auto-exposed as a callable tool a2a_<name>)
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"narrator","endpoint_url":"http://host.docker.internal:9000"}' \
  http://localhost:4444/a2a
```

### Notes

- Image pinned to `1.0.2` in `docker-compose.yml`. The upstream README still shows
  `1.0.0-RC-3` in examples; confirm the `1.0.2` tag pulls when the daemon is up.
  Fallback to `1.0.1` if `1.0.2` looks freshly churned near the deadline.
- Plugin hooks are `tool_pre_invoke` / `tool_post_invoke` / `prompt_pre_fetch` /
  `prompt_post_fetch`. Bundled plugins include PIIFilter, a rate limiter, and
  Granite Guardian. (There is no "CPEX".)
- Rollback for the observability artifact: if `/admin` does not render a clean
  4-service fan-out trace, fall back to OpenTelemetry into Jaeger or Grafana Tempo
  and screenshot that waterfall instead.

### KNOWN ISSUE: GA `latest` (arm64) hangs at startup (2026-06-02)

On Apple Silicon the GA `ghcr.io/ibm/mcp-context-forge:latest` image
(`arm64-e0967e65...`) builds all routers, logs `SECTION_PERMISSIONS validation
passed`, then **hangs in the Starlette lifespan** ("Waiting for application
startup" with no "Application startup complete"), so `:4444` never serves
(`curl` returns `000`, container is `unhealthy`). Verified it is NOT worker
contention or a corrupt DB: it still hangs with `GUNICORN_WORKERS=1` and a fresh
volume (`docker compose down -v`). `GUNICORN_WORKERS=1` is kept anyway (correct
for the local SQLite engine and removes one failure class).

**RESOLVED 2026-06-02 via option (a):** the PyPI gateway
(`pip install mcp-contextforge-gateway==1.0.2`) run on the host with a single
uvicorn worker (`mcpgateway mcpgateway.main:app --workers 1`) starts cleanly where
the Docker image hangs, so the hang is image-specific. All 4 backends register and
are reachable, the 3 tools route through the gateway with correct results
(`retrieve_law` -> Law 11, `compute_offside_margin` -> 1.75 m), and observability
recorded 10 tool executions at 100% success (~27 ms avg). Full working steps,
schemas (note: A2A registers nested under `{"agent": {...}}`, and SSRF blocks
localhost/private hosts unless `SSRF_ALLOW_LOCALHOST` / `SSRF_ALLOW_PRIVATE_NETWORKS`
are set), and the live evidence are in `docs/federation.md` ("Verified live"). The
Docker image stays pinned for reproducibility; use the PyPI path locally on arm64.
