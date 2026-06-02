from app.triggers.apifootball import parse_api_football_events


def test_parse_api_football_var_events() -> None:
    events = [
        {"type": "Var", "detail": "Goal Disallowed - offside", "time": {"elapsed": 23}},
        {"type": "Goal", "detail": "Normal Goal", "time": {"elapsed": 40}},
        {"type": "subst", "detail": "Substitution 1", "time": {"elapsed": 60}},
    ]
    out = parse_api_football_events(99, events)
    assert len(out) == 1
    assert out[0].type_name == "Var"
    assert out[0].detail == "Goal Disallowed - offside"
    assert out[0].minute == 23
    assert out[0].fixture_id == 99


def test_parse_api_football_no_var() -> None:
    assert parse_api_football_events(1, [{"type": "Goal", "detail": "Normal Goal"}]) == []
