"""A2A client: call the VARSITY narrator agent over the A2A protocol (message/send).

Resolves the agent card from /.well-known/agent-card.json, sends the decision payload
as a user message, and returns the narration the agent produced (its text artifact).
This is the round-trip that proves the narrator is reachable as a real A2A agent, not
just an in-process function call.

Pass ``httpx_client`` (an httpx.AsyncClient over httpx.ASGITransport) to talk to an
in-process app without a network port; otherwise a network client hits the live agent.
"""

from __future__ import annotations

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text, new_text_message
from a2a.types import Role, SendMessageRequest

DEFAULT_NARRATOR_URL = "http://127.0.0.1:9000"


async def narrate_via_a2a(
    payload: str,
    *,
    base_url: str = DEFAULT_NARRATOR_URL,
    httpx_client: httpx.AsyncClient | None = None,
) -> str:
    """Round-trip a decision payload through the narrator agent and return its narration."""
    owns_client = httpx_client is None
    http = httpx_client or httpx.AsyncClient(timeout=60)
    try:
        card = await A2ACardResolver(http, base_url).get_agent_card()
        agent = await create_client(card, ClientConfig(httpx_client=http, streaming=True))
        request = SendMessageRequest(message=new_text_message(payload, role=Role.ROLE_USER))
        chunks: list[str] = []
        async for event in agent.send_message(request):
            if event.HasField("artifact_update"):
                chunks.append(get_artifact_text(event.artifact_update.artifact))
            elif event.HasField("message"):
                chunks.append(get_message_text(event.message))
        await agent.close()
        return "\n".join(c for c in chunks if c).strip()
    finally:
        if owns_client:
            await http.aclose()
