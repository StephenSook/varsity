"""Tests for the Granite Vision diagram-captioning pure functions (envelope, guard, chunk)."""

from app.llm import vision
from app.rag import diagram_captions


def test_vision_messages_is_the_watsonx_image_chat_shape() -> None:
    msgs = vision.vision_messages("QUJD", "describe", mime="image/png")
    assert msgs[0]["role"] == "user"
    content = msgs[0]["content"]
    assert content[0]["type"] == "image_url"
    assert content[0]["image_url"]["url"] == "data:image/png;base64,QUJD"
    assert content[1] == {"type": "text", "text": "describe"}


def test_faithfulness_rejects_verdicts_and_ungrounded_captions() -> None:
    law = "A player is offside if nearer the goal line than the second-last opponent."
    # grounded, descriptive -> accepted
    assert vision.faithfulness_ok(
        "The diagram shows an attacker nearer the goal line than the second-last opponent.", law
    )
    # asserts a verdict -> rejected
    assert not vision.faithfulness_ok("The attacker was offside and the VAR got it wrong.", law)
    # no shared vocabulary with the Law text -> rejected (likely hallucinated)
    assert not vision.faithfulness_ok("A red car parks beside a tall building.", law)
    # empty -> rejected
    assert not vision.faithfulness_ok("   ", law)


def test_to_chunk_is_clearly_tiered() -> None:
    c = vision.to_chunk(figure_id="p107_i0", law="Law 11", caption="An offside-position diagram.")
    assert c["tier"] == "diagram-description"
    assert "AI-generated" in c["source"] and "human-reviewed" in c["source"]
    assert c["id"] == "diagram:p107_i0"


def test_model_id_is_configurable(monkeypatch) -> None:
    monkeypatch.delenv("GRANITE_VISION_MODEL_ID", raising=False)
    assert vision.vision_model_id() == vision.DEFAULT_VISION_MODEL
    monkeypatch.setenv("GRANITE_VISION_MODEL_ID", "ibm/granite-vision-4-1-4b")
    assert vision.vision_model_id() == "ibm/granite-vision-4-1-4b"


def test_loader_is_empty_until_captions_are_approved() -> None:
    # no approved file is committed (verified captions are a human-review gate), so the loader is a
    # safe no-op: unverified captions never reach the corpus.
    assert diagram_captions.approved_caption_chunks() == []
