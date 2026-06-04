"""Tests for the gateway-mediated A2A envelope (the protobuf-mapped message/send JSON-RPC)."""

from app.a2a_agent.gateway import a2a_message_send_envelope, extract_narration


def test_envelope_is_a2a_message_send_jsonrpc() -> None:
    e = a2a_message_send_envelope("explain this offside", message_id="m1", request_id="r1")
    assert e["jsonrpc"] == "2.0"
    assert e["method"] == "message/send"
    assert e["id"] == "r1"
    msg = e["params"]["message"]
    assert msg["role"] == "user"
    assert msg["messageId"] == "m1"
    assert msg["parts"] == [{"kind": "text", "text": "explain this offside"}]


def test_extract_narration_from_a_message_result() -> None:
    resp = {"result": {"parts": [{"kind": "text", "text": "the narration"}]}}
    assert extract_narration(resp) == "the narration"


def test_extract_narration_from_a_task_artifact() -> None:
    resp = {"result": {"artifacts": [{"parts": [{"kind": "text", "text": "from artifact"}]}]}}
    assert extract_narration(resp) == "from artifact"


def test_extract_narration_from_status_message() -> None:
    resp = {"result": {"status": {"message": {"parts": [{"kind": "text", "text": "status text"}]}}}}
    assert extract_narration(resp) == "status text"


def test_extract_narration_ignores_non_text_parts() -> None:
    resp = {"result": {"parts": [{"kind": "data", "data": {}}, {"kind": "text", "text": "kept"}]}}
    assert extract_narration(resp) == "kept"
