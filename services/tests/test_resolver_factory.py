"""Tests for the env-gated live VAR-feed client factory."""

from app.triggers import resolver


def test_no_keys_returns_no_clients(monkeypatch) -> None:
    monkeypatch.delenv("SPORTMONKS_API_KEY", raising=False)
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    assert resolver.live_clients() == (None, None)


def test_placeholder_key_is_treated_as_absent(monkeypatch) -> None:
    monkeypatch.setenv("SPORTMONKS_API_KEY", "changeme")
    monkeypatch.setenv("API_FOOTBALL_KEY", "")
    assert resolver.live_clients() == (None, None)


def test_real_keys_instantiate_the_clients(monkeypatch) -> None:
    monkeypatch.setenv("SPORTMONKS_API_KEY", "real-token-123")
    monkeypatch.setenv("API_FOOTBALL_KEY", "real-token-456")
    sportmonks, apifootball = resolver.live_clients()
    assert sportmonks is not None and apifootball is not None


def test_resolver_with_no_clients_falls_to_the_replay_floor() -> None:
    # the deterministic demo floor is unchanged: no clients passed -> replay buffer
    events, source = resolver.resolve_live_var_events()
    assert source == "replay-buffer"
    assert events
