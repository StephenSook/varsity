from starlette.testclient import TestClient

from app.a2a_agent.narrator import build_app, narrate


class FakeGranite:
    def __init__(self) -> None:
        self.calls: list = []

    def explain_offside(self, *, margin_meters, is_offside, law_text, language="English"):
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
