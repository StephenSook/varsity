"""IBM watsonx connectivity check via the raw ML REST API (no fragile SDK).

Loads creds from .env, exchanges the API key for an IAM bearer token, lists the
Granite foundation models the account can use, and runs a one-line Granite
inference. Prints model ids and the short output only, never the key or token.
Use the printed model id to pin GRANITE_MODEL_ID.

Run from anywhere:  python services/scripts/check_watsonx.py
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

api_key = os.environ.get("WATSONX_API_KEY", "")
project_id = os.environ.get("WATSONX_PROJECT_ID", "")
url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/")
API_VERSION = "2024-05-31"

if not api_key or api_key.startswith("your_") or not project_id or project_id.startswith("your_"):
    print("WATSONX_API_KEY / WATSONX_PROJECT_ID missing or placeholder in .env")
    raise SystemExit(1)


def iam_token(key: str) -> str:
    resp = httpx.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": key},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"IAM token exchange FAILED (HTTP {resp.status_code}) - check the API key")
        raise SystemExit(1)
    return resp.json()["access_token"]


try:
    token = iam_token(api_key)
    auth = {"Authorization": f"Bearer {token}"}
    print("IAM auth OK")

    specs = httpx.get(
        f"{url}/ml/v1/foundation_model_specs",
        params={"version": API_VERSION, "limit": 200},
        headers=auth,
        timeout=30,
    )
    print(f"model specs HTTP {specs.status_code}")
    resources = specs.json().get("resources", []) if specs.status_code == 200 else []
    granite = sorted(
        {r.get("model_id", "") for r in resources if "granite" in r.get("model_id", "").lower()}
    )
    print(f"granite text models ({len(granite)}):")
    for mid in granite:
        print("   ", mid)

    candidates = [m for m in granite if "instruct" in m.lower()] or granite
    if not candidates:
        print("  RESULT: FAIL (no granite model for this account/region)")
        raise SystemExit(1)

    mid = candidates[0]
    gen = httpx.post(
        f"{url}/ml/v1/text/generation",
        params={"version": API_VERSION},
        headers={**auth, "Content-Type": "application/json"},
        json={
            "model_id": mid,
            "input": "Reply with one word: ready.",
            "project_id": project_id,
            "parameters": {"max_new_tokens": 5, "decoding_method": "greedy"},
        },
        timeout=60,
    )
    print(f"inference HTTP {gen.status_code}")
    if gen.status_code == 200:
        text = gen.json()["results"][0]["generated_text"]
        print(f"  [{mid}] -> {text!r}")
        print(f"  PIN THIS -> GRANITE_MODEL_ID={mid}")
        print("  RESULT: PASS")
    else:
        print("  RESULT: FAIL (inference rejected - associate the WML Runtime with the project)")
        raise SystemExit(1)
except SystemExit:
    raise
except Exception as exc:
    print(f"watsonx error: {type(exc).__name__}")
    print("  RESULT: FAIL")
    raise SystemExit(1) from None
