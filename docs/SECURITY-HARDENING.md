# Security hardening: corpus integrity + oracle input

VARSITY's safety story is defense-in-depth around a blind user who cannot visually
fact-check what they hear, so an over-confident wrong answer is the worst failure. The
existing layers (Granite Guardian groundedness, the deterministic verification panel, the
fail-closed Law-quoting floor, the SHA-256 provenance manifest) screen the model OUTPUT.
This wave hardens two inputs: the RAG corpus and the free-text oracle.

In concept throughout: these screen and ground a safe explanation of a RECEIVED decision.
They never adjudicate.

## SHA-256 Law-corpus signing (OWASP LLM08: data/model poisoning)

`services/app/rag/corpus_signature.py` · endpoint `GET /corpus_integrity`

The corpus (`rag/index/chunks.json`) is the grounding for every spoken rule claim. A
poisoned Law chunk would silently corrupt an explanation the user cannot check. So:

- each chunk is hashed (`SHA-256` over canonical `{law,title,text}` JSON), and a single
  **root hash** is taken over the sorted per-chunk digests, into a signed manifest
  (`rag/index/chunks.sig.json`, committed);
- the retriever **verifies the canonical corpus on load and fails CLOSED** on any mismatch
  (`CorpusIntegrityError`), a tampered, added, or removed Law is caught before retrieval;
- custom corpora (test fixtures) carry no manifest, so they skip verification;
- re-sign after any deliberate corpus edit: `python -m app.rag.corpus_signature`.

Deterministic, no model, no network, the auditable boundary OWASP wants paired with the
probabilistic Guardian. A tampered corpus is caught by arithmetic, not by a model that
might miss it.

## Oracle input hardening (OWASP LLM01: prompt injection)

`services/app/safety/input_screen.py` · `safety/hap.py`

The "ask any rule" oracle takes a fan's free-text question and feeds it to Granite, the
one place untrusted text reaches the model. Three layers:

1. **Deterministic HAP screen (always-on floor).** A hate/abuse/profanity wordlist screen.
   Football vocabulary does not overlap it, so false positives are unlikely. On a hit the
   oracle declines, no model call.
2. **Deterministic prompt-injection / jailbreak screen.** Targets the canonical override
   phrasings: "ignore previous instructions", system-prompt probes, role-override
   ("you are now...", "act as..."), delimiter breakouts (`<|...|>`, ```` ```system ````, `[INST]`).
3. **Spotlighting (delimiting).** Even a clean question is wrapped as quoted DATA between
   `<<<FAN_QUESTION>>>` markers in the Granite prompt, which instructs the model to treat
   it strictly as a question, never as instructions. A user cannot smuggle a closing
   delimiter to break out.

On a HAP or injection hit the oracle **fails closed**: it declines in the fan's language,
the question is **withheld** from the model (never echoed back), and a terminal `verdict`
is still emitted so the screen reader gets a spoken reply. The decline is the same neutral
behaviour the oracle already uses for off-topic questions.

### The HAP model tier (honest framing)

`safety/hap.py` encodes the IBM model tier behind the deterministic floor, with the
feasibility-verified caveats:

- watsonx.ai text/generation exposes a `moderations.hap` guardrail on input **and** output
  (threshold + span masking). `_watsonx.generate` accepts an optional `moderations`
  passthrough (default `None`, zero risk to existing callers); pass
  `hap.watsonx_moderation_payload()` to enable it. **Caveat:** IBM documents the watsonx
  HAP detector as a **Slate-family** classifier, not confirmably `granite-guardian-hap-38m`.
- `ibm-granite/granite-guardian-hap-38m` (**Apache-2.0**, a RoBERTa-4-layer binary toxicity
  classifier) is the named small HAP model. There is **no official in-browser ONNX build
  today** (only a third-party conversion), so an on-device HAP screen would need a
  self-converted export, we do **not** claim a drop-in on-device model.

The always-on gate is therefore the deterministic floor (offline, sub-millisecond); the
watsonx guardrail is the optional heavier tier, enabled with one parameter.

## What is intentionally NOT here (honest)

- The full live-feed **quarantined-data** pattern is only needed when untrusted player-name
  strings reach the narrator's prompt. On the canned StatsBomb path the frame carries role
  booleans, not names; on the live Sportmonks path the raw feed text appears in the
  transitional SSE stage (shown to the user) but does **not** enter the Granite prompt, so
  the injection surface there is small. The oracle, which does feed free text to the model,
  is the surface hardened here.
- A Guardian non-adjudication BYOC *neutrality* criterion is **already enforced
  deterministically** by the `no-re-adjudication` critic in `verification.py`; adding a
  second live Guardian call for it is deferred (verify-first the model id; cost).
