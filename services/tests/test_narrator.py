import asyncio

import httpx
from starlette.testclient import TestClient

from app.a2a_agent.client import narrate_via_a2a
from app.a2a_agent.narrator import build_app, narrate


class FakeGranite:
    def __init__(self) -> None:
        self.calls: list = []

    def explain_offside(self, *, margin_meters, is_offside, law_text, language="English", **_):
        self.calls.append((margin_meters, is_offside, language))
        return f"[{language}] offside by {margin_meters} meters (Law 11)"


def test_narrate_parses_decision_json() -> None:
    g = FakeGranite()
    out = narrate(
        '{"margin_meters": 5.45, "is_offside": true, "law_text": "Law 11", "language": "Spanish"}',
        granite=g,
    )
    assert "5.45" in out
    assert g.calls[0] == (5.45, True, "Spanish")


def test_narrate_falls_back_on_bad_payload() -> None:
    g = FakeGranite()
    out = narrate("not a decision", granite=g)
    assert "Law 11" in out
    assert g.calls[0][0] == 5.45  # canned WC2022 fallback


def test_agent_card_served_at_well_known() -> None:
    client = TestClient(build_app(granite=FakeGranite()))
    resp = client.get("/.well-known/agent-card.json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "VARSITY Narrator"
    assert any(s["id"] == "narrate_offside" for s in body["skills"])


def test_a2a_message_send_round_trip() -> None:
    """A real A2A client resolves the card, sends message/send, reads the narration.

    Runs fully in-process over httpx.ASGITransport, so it exercises the actual A2A
    JSON-RPC server + client (card resolution, user message, artifact response) with
    no network and no watsonx (FakeGranite).
    """
    app = build_app(granite=FakeGranite())
    url = "http://127.0.0.1:9000"

    async def run() -> str:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=url) as http:
            return await narrate_via_a2a(
                '{"margin_meters": 5.45, "is_offside": true, "law_text": "Law 11"}',
                base_url=url,
                httpx_client=http,
            )

    out = asyncio.run(run())
    assert "offside by 5.45 meters" in out.lower()  # the FakeGranite narration came back
    assert "Law 11" in out
