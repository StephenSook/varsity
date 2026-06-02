from app.triggers.replay import CANNED_REVIEW, ReplayBuffer, canned_buffer
from app.triggers.resolver import pick_transitional, resolve_live_var_events, reviewing_stage
from app.triggers.sportmonks import VarEvent


def test_canned_buffer_has_transitional_then_final() -> None:
    evs = canned_buffer().events()
    assert len(evs) == 2
    assert evs[0].transitional is True  # Goal Under Review (transitional)
    assert evs[1].transitional is False  # final outcome
    assert "offside" in (evs[1].detail or "").lower()


def test_replay_buffer_record_and_empty() -> None:
    buf = ReplayBuffer()
    assert buf.empty() is True
    buf.record([VarEvent(0, 10, "VAR", "x")])
    assert buf.empty() is False


class _Empty:
    def live_var_events(self):
        return []


class _Boom:
    def live_var_events(self):
        raise RuntimeError("network down")


class _Has:
    def live_var_events(self):
        return [VarEvent(7, 12, "Var", "Goal Disallowed - offside")]


def test_resolver_prefers_first_non_empty_live_source() -> None:
    events, source = resolve_live_var_events(sportmonks=_Empty(), apifootball=_Has())
    assert source == "api-football"
    assert events[0].fixture_id == 7


def test_resolver_sportmonks_wins_when_present() -> None:
    _events, source = resolve_live_var_events(sportmonks=_Has(), apifootball=_Empty())
    assert source == "sportmonks"


def test_resolver_falls_back_to_replay_when_all_fail() -> None:
    events, source = resolve_live_var_events(sportmonks=_Boom(), apifootball=_Empty())
    assert source == "replay-buffer"
    assert events == list(CANNED_REVIEW)


def test_resolver_replay_when_no_clients() -> None:
    events, source = resolve_live_var_events()
    assert source == "replay-buffer"
    assert len(events) == 2


def test_reviewing_stage_and_pick_transitional() -> None:
    t = pick_transitional(canned_buffer().events())
    assert t is not None and t.transitional is True
    stage = reviewing_stage(t, "replay-buffer")
    assert stage["stage"] == "reviewing"
    assert stage["source"] == "replay-buffer"
    assert "reviewing" in (stage["detail"] or "").lower()
