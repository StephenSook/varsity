"""Discourse state over a sequence of RECEIVED VAR decisions in a match.

As a fan steps through the VAR moments of a match, VARSITY can refer back to the decisions it has
already explained: "the second tight call so far", "the same outcome as the previous review", "in
contrast to the previous onside". This is discourse cohesion over RECEIVED, already-explained
decisions. It records what the officials decided and references it; it never predicts, recomputes,
or adjudicates a call. The state is populated only after a decision has been received and explained.

The store is per-match and in-memory (a match is a short session); a re-view of the same moment is
deduplicated, so re-clicking one scenario never inflates the counts. The pure functions
(``connective``/``record``) are the tested core; the module store is a thin accessor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_TIGHT_BANDS = {"tight", "very tight"}
_ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth"}


def _ordinal(n: int) -> str:
    return _ORDINALS.get(n, f"{n}th")


@dataclass(frozen=True)
class DecisionRecord:
    key: str  # a stable id for the moment (verdict + rounded margin), to dedupe re-views
    is_offside: bool
    band: str


@dataclass
class MatchState:
    history: list[DecisionRecord] = field(default_factory=list)

    @property
    def tight_count(self) -> int:
        return sum(1 for d in self.history if d.band in _TIGHT_BANDS)


def connective(state: MatchState, *, key: str, is_offside: bool, band: str) -> str:
    """The discourse lead-in to prepend, computed BEFORE recording this decision. Empty for the
    first decision of the match or for a re-view of the immediately-previous moment."""
    history = state.history
    if history and history[-1].key == key:
        return ""  # re-viewing the same moment adds no new discourse
    if not history:
        return ""
    parts: list[str] = []
    if band in _TIGHT_BANDS:
        parts.append(f"the {_ordinal(state.tight_count + 1)} tight call so far")
    last = history[-1]
    if last.is_offside == is_offside:
        parts.append("the same outcome as the previous review")
    else:
        parts.append(f"in contrast to the previous {'offside' if last.is_offside else 'onside'} review")
    return "; ".join(parts)


def record(state: MatchState, *, key: str, is_offside: bool, band: str) -> None:
    """Append this received decision unless it repeats the immediately-previous moment."""
    if state.history and state.history[-1].key == key:
        return
    state.history.append(DecisionRecord(key=key, is_offside=is_offside, band=band))


def moment_key(is_offside: bool, margin_meters: float) -> str:
    """A stable id for a freeze-frame moment, so re-viewing it does not inflate the discourse."""
    return f"{is_offside}:{round(margin_meters, 2)}"


_STORE: dict[str, MatchState] = {}


def for_match(match_id: str) -> MatchState:
    return _STORE.setdefault(match_id, MatchState())


def reset_match(match_id: str) -> None:
    _STORE.pop(match_id, None)
