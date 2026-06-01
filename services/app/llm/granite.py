"""IBM Granite reasoning client (watsonx ML REST API).

Uses the raw watsonx ML REST API rather than the ibm-watsonx-ai SDK (which has a
broken import in the installed version). Flow: exchange the IBM Cloud API key for
an IAM bearer token (cached until shortly before expiry), then call
``/ml/v1/text/generation`` with a Granite model. Reads config from the environment
(loaded from .env by the caller); never logs the key or token.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
API_VERSION = "2024-05-31"
DEFAULT_URL = "https://us-south.ml.cloud.ibm.com"
DEFAULT_MODEL = "ibm/granite-4-h-small"


@dataclass
class GraniteConfig:
    api_key: str
    project_id: str
    url: str
    model_id: str

    @classmethod
    def from_env(cls) -> GraniteConfig:
        url = os.environ.get("WATSONX_URL", DEFAULT_URL).rstrip("/")
        return cls(
            api_key=os.environ["WATSONX_API_KEY"],
            project_id=os.environ["WATSONX_PROJECT_ID"],
            url=url,
            model_id=os.environ.get("GRANITE_MODEL_ID", DEFAULT_MODEL),
        )


class GraniteClient:
    """Minimal, dependency-light Granite text-generation client."""

    def __init__(self, config: GraniteConfig | None = None) -> None:
        self.config = config or GraniteConfig.from_env()
        self._token: str | None = None
        self._token_exp: float = 0.0

    def _bearer(self) -> str:
        now = time.time()
        if self._token and now < self._token_exp - 60:
            return self._token
        resp = httpx.post(
            IAM_URL,
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self.config.api_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_exp = now + int(body.get("expires_in", 3600))
        return self._token

    def generate(self, prompt: str, *, max_new_tokens: int = 200, decoding: str = "greedy") -> str:
        resp = httpx.post(
            f"{self.config.url}/ml/v1/text/generation",
            params={"version": API_VERSION},
            headers={
                "Authorization": f"Bearer {self._bearer()}",
                "Content-Type": "application/json",
            },
            json={
                "model_id": self.config.model_id,
                "input": prompt,
                "project_id": self.config.project_id,
                "parameters": {"max_new_tokens": max_new_tokens, "decoding_method": decoding},
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["results"][0]["generated_text"].strip()

    def explain_offside(
        self,
        *,
        margin_meters: float,
        is_offside: bool,
        law_text: str,
        language: str = "English",
    ) -> str:
        """Generate a plain-language, Law-grounded explanation of an offside decision."""
        verdict = "offside" if is_offside else "onside"
        relation = "ahead of" if is_offside else "behind"
        prompt = (
            "You are explaining a soccer VAR offside decision to a blind fan in plain, "
            f"warm language. Reply in {language}, in 2 to 3 short sentences. Ground the "
            "explanation in the Law text below and cite the Law number. Do not invent any "
            "rule that is not in the Law text.\n\n"
            f"Law text:\n{law_text}\n\n"
            "Decision data: the most advanced attacker was "
            f"{abs(margin_meters):.2f} meters {relation} the second-to-last defender when "
            f"the ball was played. Verdict: {verdict}.\n\nExplanation:"
        )
        return self.generate(prompt, max_new_tokens=180)
