"""IBM watsonx HAP (hate / abuse / profanity) moderation - the model tier behind the
deterministic floor in ``input_screen.py``.

VERIFIED (2026-06-03, honesty-gated). Two honest facts that this module encodes:

- watsonx.ai text/generation exposes a ``moderations.hap`` guardrail on input AND output
  (threshold + span masking). It is the confirmable IBM-tool integration: pass
  ``watsonx_moderation_payload()`` to ``llm._watsonx.generate(..., moderations=...)`` and
  watsonx screens the prompt and the completion. CAVEAT: IBM documents the watsonx HAP
  detector as a Slate-family classifier, NOT confirmably ``granite-guardian-hap-38m``; the
  only named Granite Guardian served on watsonx is the 8B risk model.
- ``ibm-granite/granite-guardian-hap-38m`` (Apache-2.0, a RoBERTa-4-layer binary toxicity
  classifier, label 1 = toxic) is the named small HAP model. There is NO official
  in-browser ONNX build today (only a third-party conversion), so an on-device HAP screen
  would require a self-converted export - we do NOT claim a drop-in on-device model.

The ALWAYS-ON gate is the deterministic ``input_screen`` floor (offline, sub-millisecond);
this watsonx guardrail is the optional heavier tier, enabled with one parameter.
"""

from __future__ import annotations

# The named small HAP model (the documented model tier; Apache-2.0).
HAP_MODEL_ID = "ibm-granite/granite-guardian-hap-38m"
HAP_MODEL_LICENSE = "Apache-2.0"


def watsonx_moderation_payload(threshold: float = 0.5, *, mask: bool = True) -> dict:
    """Build the watsonx text/generation ``moderations.hap`` guardrail config (input +
    output). Threshold 1.0 disables; lower is stricter. ``mask`` redacts the flagged span.
    """
    cfg: dict = {"enabled": True, "threshold": threshold}
    if mask:
        cfg["mask"] = {"remove_entity_value": True}
    return {"hap": {"input": dict(cfg), "output": dict(cfg)}}
