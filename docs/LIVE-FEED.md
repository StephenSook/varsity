# Live feed: schema, fusion, pre-warm, and honest latency

VARSITY's live trigger turns a real VAR review into a spoken, rule-grounded explanation
before the broadcast picture catches up. This is the robustness layer behind that path.
It is a flourish, never load-bearing: the canned StatsBomb 360 path and the recorded
replay buffer are the deterministic floor, so the demo never depends on a live match.

Everything here stays in concept. The feed carries a **received** decision (what the
officials signalled) to the explainer. Nothing here predicts or adjudicates a call.

## 1. Normalized `VARDecisionEvent` schema + feed adapters

`services/app/triggers/schema.py`

Every source (Sportmonks, API-Football, the replay buffer, StatsBomb 360) is an
**adapter** that emits the same `VARDecisionEvent`, so the explainer depends only on the
schema, never on a source's raw payload (hexagonal ports-and-adapters). The schema is the
seam the fusion and pre-warm layers build on.

| Field | Meaning |
|---|---|
| `event_id` | adapter-prefixed (`sportmonks:998:10`) so feeds never collide and dedup is exact |
| `source` | `sportmonks` / `api-football` / `replay-buffer` / `statsbomb360` |
| `phase` | `review_started` (no outcome yet) or `review_resolved` (the official's result) |
| `review_reason` | a coarse label only (Offside / Handball / Penalty) - never the decision |
| `outcome` | the official's signalled result; **null while a review is in progress** (no guess) |
| `confidence` | filled by the fusion layer (1.0 for the deterministic replay floor) |
| `geometry_ref` | the freeze-frame backing the explanation, if any |

`dedup_and_sort` dedups on `event_id` (a feed repeats an event across polls) and orders by
`sort_order` then `minute`. It **never** orders by minute alone: Sportmonks events carry no
per-event timestamp and several can share a minute, so `sort_order` (the feed's own order)
is the key.

## 2. Multi-source fusion confidence

`services/app/triggers/fusion.py` · endpoint `GET /fusion`

Two feeds can each report the same review. When they **agree** we are more confident; when
only one has fired we **hedge**; when they **conflict** we surface the conflict and stay
unconfirmed. This raises confidence and resilience - it never adjudicates.

| Situation | Confidence | Narration hedge |
|---|---|---|
| `review_started` (transitional, Sportmonks-only) | 0.70 | "A VAR review appears to be underway." |
| `review_resolved`, one source | 0.85 | "Confirmed by sportmonks." |
| `review_resolved`, two sources agree | 0.91 | "Confirmed by multiple feeds (...)." |
| three+ sources agree | 0.97 (cap) | "Confirmed by multiple feeds (...)." |
| sources **conflict** on the outcome | 0.50, `outcome=null` | "Feeds disagree...; treating it as unconfirmed." |
| replay / canned floor | 1.0 | deterministic |

On a conflict we report **no** outcome. We never pick a side. The confidence pairs with
the Wave-A uncertainty band: a low confidence makes the narrator hedge rather than assert.

## 3. Speculative pre-warm

`services/app/triggers/prewarm.py` · wired into `GET /stream/live`

A VAR review has a gap: the officials signal "under review", then 15-45s later the outcome.
We use that gap. On `review_started` the pipeline pre-computes the **outcome-independent**
work - retrieve the Law and run the freeze-frame geometry - and caches it keyed by the
review. When the official outcome lands, the resolved explanation reuses the cached Law
(`explanation_stages(..., prewarmed_law=...)` skips its own retrieval), so the
trigger -> spoken-verdict path skips that cold work.

Honesty: pre-warm caches **facts** (the rule text and the geometry of the frozen moment),
never a verdict. Both outcome branches (goal disallowed / goal confirmed) are prepared from
those facts; the official's received decision selects which one is spoken. We never predict
the call - we prepare to explain whichever call arrives.

## 4. Honest latency framing

`services/app/latency.py` · endpoint `GET /latency`

The thesis is "first in the room": a blind fan hears the why before the broadcast picture
catches up to the on-field moment. The figure has to be honest, not the false "4-8s" (that
is the optimization target for low-latency LL-HLS *streaming*, not the real
glass-to-glass-from-the-field delay a fan actually experiences).

Verified broadcast delay behind the field of play, per delivery path:

| Path | Delay we cite | Source |
|---|---|---|
| Over-the-air (OTA) | ~18s (the hardest to beat) | Phenix 2023 (~18s), 2024 (~22.19s) |
| Cable | ~28s (up to ~50s) | Phenix 2023 / 2024 |
| OTT / streaming | ~35s typical (30-60s+, worse for live sports) | HLS/DASH; Phenix per-app 24-86s |

Primary source: Phenix "Field of Play" Super Bowl latency studies, reported via
Sports Video Group (2024-02-12). VARSITY targets a **trigger -> spoken-verdict budget of
10s** (`LATENCY_BUDGET_S`), which beats every path with comfortable margin.

**Honesty caveat (shipped in the payload):** Phenix is a low-latency-streaming vendor (a
commercial interest in large delay figures), and the measurement is field-of-play (the
whole camera-to-air production chain), not pure encoder-to-display transmission (~5-12s).
The field-of-play framing is the right one here: the blind fan is racing the actual
on-field event, not the encoder. The `BroadcastTicker` shows a real measured delta for the
run (the broadcast offset minus VARSITY's own measured latency), never a hardcoded lead.

## Feed gotchas (verify-first when wiring a live source)

- **Dedup on the integer `id`**, never on minute (Sportmonks events have no per-event
  timestamp). Sort by `sort_order`.
- Poll `/livescores/inplay?include=events;state`, not `/livescores/latest` (which does not
  fire on new events). Both Sportmonks and API-Football are **poll-only** (no webhooks).
- Sportmonks VAR `type_id=10`; `info` = reason ("Offside"), `addition` = outcome
  ("Goal Disallowed"), null during "Goal under review". API-Football emits **final
  outcomes only** (no transitional state), so Sportmonks stays primary.
- **StatsBomb 360 is historical only**, with role booleans (teammate / actor / keeper) and
  no player ids for non-actors - so "the attacker who received the ball", never a named
  player's exact margin. Live non-open-data matches degrade to the stylized pitch + textual
  reason, never fabricated frames.
