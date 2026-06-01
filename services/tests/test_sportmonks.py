from app.triggers.sportmonks import parse_var_events


def test_parse_var_events_detects_var_by_type() -> None:
    events = [
        {"type": {"name": "Goal"}, "minute": 12},
        {"type": {"name": "VAR"}, "minute": 34, "info": "Goal Disallowed - offside"},
        {"type": {"name": "Substitution"}, "minute": 60},
    ]
    out = parse_var_events(101, events)
    assert len(out) == 1
    assert out[0].fixture_id == 101
    assert out[0].minute == 34
    assert "offside" in (out[0].detail or "").lower()


def test_parse_var_events_detects_via_detail() -> None:
    events = [{"type": {"name": "Goal"}, "minute": 5, "info": "disallowed offside"}]
    assert len(parse_var_events(7, events)) == 1


def test_parse_var_events_ignores_normal_play() -> None:
    events = [{"type": {"name": "Corner"}, "minute": 22}]
    assert parse_var_events(7, events) == []
