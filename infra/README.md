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

### Register a backend (federation)

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
