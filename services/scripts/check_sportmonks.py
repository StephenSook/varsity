"""Sportmonks connectivity check. Loads the token from .env, never prints it.

Auth is sent in the Authorization header (not the URL query) so the token cannot
leak into logs or tracebacks. Output is sanitized: status + non-secret sample only.

Run from anywhere:  python services/scripts/check_sportmonks.py
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

token = os.environ.get("SPORTMONKS_API_KEY", "")
if not token or token.startswith("your_"):
    print("SPORTMONKS_API_KEY missing or still a placeholder in .env")
    raise SystemExit(1)

try:
    resp = httpx.get(
        "https://api.sportmonks.com/v3/football/leagues",
        headers={"Authorization": token},
        params={"per_page": 5},
        timeout=20,
    )
    print(f"Sportmonks HTTP {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json().get("data", [])
        names = [d.get("name") for d in data][:5]
        print(f"  accessible leagues (sample): {names}")
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL (status {resp.status_code} - check the token / plan)")
        raise SystemExit(1)
except SystemExit:
    raise
except Exception as exc:  # never print str(exc): could echo the request URL
    print(f"Sportmonks error: {type(exc).__name__}")
    print("  RESULT: FAIL")
    raise SystemExit(1) from None
