import pytest

from app import ratelimit


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    # Reset the per-IP stream rate limiter before each test so cumulative TestClient calls
    # across the suite (all from one "testclient" IP) never trip the limit unintentionally.
    ratelimit.reset()
    yield
