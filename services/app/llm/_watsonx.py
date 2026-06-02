"""Shared watsonx ML REST helpers: IAM token caching, text generation, embeddings.

Single place for the raw watsonx ML REST calls (the ibm-watsonx-ai SDK has a broken
import in the installed version). Reads WATSONX_API_KEY / WATSONX_PROJECT_ID /
WATSONX_URL from the environment. Never logs the key or token.
"""

from __future__ import annotations

import os
import time

import httpx

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
API_VERSION = "2024-05-31"
DEFAULT_URL = "https://us-south.ml.cloud.ibm.com"

_token: dict[str, object] = {"value": None, "exp": 0.0}


def _base_url() -> str:
    return os.environ.get("WATSONX_URL", DEFAULT_URL).rstrip("/")


def bearer() -> str:
    """Exchange the API key for an IAM bearer token, cached until shortly before expiry."""
    now = time.time()
    cached = _token["value"]
    if isinstance(cached, str) and now < float(_token["exp"]) - 60:
        return cached
    resp = httpx.post(
        IAM_URL,
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": os.environ["WATSONX_API_KEY"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    _token["value"] = body["access_token"]
    _token["exp"] = now + int(body.get("expires_in", 3600))
    return body["access_token"]


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {bearer()}", "Content-Type": "application/json"}


def generate(
    model_id: str,
    prompt: str,
    *,
    max_new_tokens: int = 200,
    min_new_tokens: int | None = None,
    decoding: str = "greedy",
) -> str:
    parameters: dict[str, object] = {
        "max_new_tokens": max_new_tokens,
        "decoding_method": decoding,
    }
    if min_new_tokens is not None:
        parameters["min_new_tokens"] = min_new_tokens
    resp = httpx.post(
        f"{_base_url()}/ml/v1/text/generation",
        params={"version": API_VERSION},
        headers=_auth(),
        json={
            "model_id": model_id,
            "input": prompt,
            "project_id": os.environ["WATSONX_PROJECT_ID"],
            "parameters": parameters,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["results"][0]["generated_text"].strip()


def chat(model_id: str, messages: list[dict], *, max_tokens: int = 8) -> str:
    """Chat-completions call. Granite Guardian needs the chat template applied (the
    raw text/generation endpoint does not trigger its risk-classification head), so
    the Guardian path uses this rather than ``generate``."""
    resp = httpx.post(
        f"{_base_url()}/ml/v1/text/chat",
        params={"version": API_VERSION},
        headers=_auth(),
        json={
            "model_id": model_id,
            "messages": messages,
            "project_id": os.environ["WATSONX_PROJECT_ID"],
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def embed(model_id: str, texts: list[str]) -> list[list[float]]:
    resp = httpx.post(
        f"{_base_url()}/ml/v1/text/embeddings",
        params={"version": API_VERSION},
        headers=_auth(),
        json={
            "model_id": model_id,
            "inputs": texts,
            "project_id": os.environ["WATSONX_PROJECT_ID"],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return [r["embedding"] for r in resp.json()["results"]]
