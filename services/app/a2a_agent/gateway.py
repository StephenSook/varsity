"""Gateway-mediated A2A invocation.

The direct round-trip (``client.narrate_via_a2a``) reaches the narrator on its own port. This module
drives the SAME narrator THROUGH the Context Forge gateway using the A2A ``message/send`` JSON-RPC
envelope (the protobuf-mapped JSON: a typed text part + a messageId), which is what the gateway's
federated-agent RPC expects (a flat body does not drive it). It proves the narrator is reachable as
a federated A2A agent behind the gateway, not only on its direct port.

The envelope builder and the narration extractor are pure and unit-tested. The POST itself is
verify-first: the exact RPC path depends on the gateway version, so run it against a live gateway
(``docs/federation.md``). This module deliberately imports no a2a-sdk or httpx at load time, so the
pure helpers are testable without those dependencies present.
"""

from __future__ import annotations

from typing import Any


def a2a_message_send_envelope(payload: str, *, message_id: str, request_id: str) -> dict[str, Any]:
    """The A2A ``message/send`` JSON-RPC request (protobuf-mapped JSON): a text part carrying the
    decision payload, addressed to the narrator. Pure, no network."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": payload}],
                "messageId": message_id,
            }
        },
    }


def extract_narration(response: dict[str, Any]) -> str:
    """Pull the narration text out of an A2A ``message/send`` result, whether the agent returned a
    Message (``parts``), a Task with ``artifacts``, or a ``status.message`` with parts."""
    result = response.get("result", response)
    texts: list[str] = []

    def _collect(parts: Any) -> None:
        for p in parts or []:
            if isinstance(p, dict) and p.get("kind") == "text" and p.get("text"):
                texts.append(str(p["text"]))

    if isinstance(result, dict):
        _collect(result.get("parts"))
        for art in result.get("artifacts") or []:
            if isinstance(art, dict):
                _collect(art.get("parts"))
        status_msg = (result.get("status") or {}).get("message") or {}
        if isinstance(status_msg, dict):
            _collect(status_msg.get("parts"))
    return "\n".join(texts).strip()


async def gateway_narrate(
    payload: str,
    *,
    gateway_url: str,
    rpc_path: str = "/a2a/varsity-narrator",
    message_id: str,
    request_id: str,
    httpx_client: Any | None = None,
) -> str:
    """POST the A2A envelope to the gateway's federated-agent RPC endpoint and return the narration.
    Verify-first: confirm ``rpc_path`` against the running gateway version before relying on it."""
    import httpx

    envelope = a2a_message_send_envelope(payload, message_id=message_id, request_id=request_id)
    owns = httpx_client is None
    http = httpx_client or httpx.AsyncClient(timeout=60)
    try:
        resp = await http.post(gateway_url.rstrip("/") + rpc_path, json=envelope)
        resp.raise_for_status()
        return extract_narration(resp.json())
    finally:
        if owns:
            await http.aclose()
