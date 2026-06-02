# Deploying VARSITY

VARSITY is two deployables: the FastAPI backend (the explanation pipeline + SSE) and
the Vite front end. The canned StatsBomb path is the deterministic floor, so the live
demo works without any live sports feed.

## Backend

Secrets are set in the platform's environment, never committed. Required:
`WATSONX_API_KEY`, `WATSONX_PROJECT_ID` (set `sync: false` / secret). Defaulted in
`render.yaml`: `WATSONX_URL`, `GRANITE_MODEL_ID`, `GRANITE_GUARDIAN_MODEL_ID`,
`GRANITE_EMBED_MODEL_ID`. Optional: `SPORTMONKS_API_KEY` for the live trigger.

### Option A - IBM Cloud Code Engine (on-theme: IBM challenge, IBM Cloud)

```bash
ibmcloud login --sso
ibmcloud target -g <resource-group> -r us-south
ibmcloud ce project create --name varsity
# watsonx secrets as a Code Engine secret
ibmcloud ce secret create --name varsity-watsonx --from-literal WATSONX_API_KEY=*** --from-literal WATSONX_PROJECT_ID=***
# build from this public repo + the services Dockerfile, deploy with a public URL
ibmcloud ce app create --name varsity-api \
  --build-source https://github.com/StephenSook/varsity \
  --build-context-dir services --build-dockerfile Dockerfile \
  --port 8000 --env-from-secret varsity-watsonx \
  --env WATSONX_URL=https://us-south.ml.cloud.ibm.com \
  --env GRANITE_MODEL_ID=ibm/granite-4-h-small \
  --env GRANITE_GUARDIAN_MODEL_ID=ibm/granite-guardian-3-8b \
  --min-scale 1
ibmcloud ce app get --name varsity-api --output url
```

### Option B - Render (one click)

New > Blueprint > point at this repo. `render.yaml` provisions `varsity-api` from
`services/Dockerfile` with `/health` checks. Set `WATSONX_API_KEY` +
`WATSONX_PROJECT_ID` (and optionally `SPORTMONKS_API_KEY`) in the dashboard.

### Verify

```bash
curl https://<backend-url>/health           # {"status":"ok",...}
curl -N https://<backend-url>/stream/canned  # SSE: trigger -> ... -> verdict
```

## Front end (Vercel)

Import the repo on Vercel. Root directory `apps/web` (Vercel auto-detects Vite:
build `npm run build`, output `dist`). Set one env var:

```
VITE_BACKEND_URL = https://<backend-url>
```

Redeploy. The front end then streams from the deployed backend; the on-device
offline mode still works with no backend at all.

## Notes

- CORS on the backend currently allows all origins (demo). Tighten to the Vercel
  domain via an allowlist before any non-demo use.
- The backend image installs the full `requirements.txt` (includes the MCP + A2A
  SDKs used by the federation servers). The federation MCP/A2A servers and the
  Context Forge gateway are run separately (see `docs/federation.md`); the public
  API does not need them to serve `/stream/*`.
