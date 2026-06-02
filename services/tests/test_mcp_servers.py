from app.mcp_servers.geometry_server import compute_offside_margin
from app.mcp_servers.ifab_rag import retrieve_law


def test_retrieve_law_returns_offside_law() -> None:
    out = retrieve_law("offside attacker nearer the goal line than the second-last defender")
    assert out["law"] == "11"
    assert out["title"] == "Offside"
    assert "offside" in out["text"].lower()


def test_compute_offside_margin_offside() -> None:
    players = [
        {"x": 100.0, "y": 40.0, "teammate": True},
        {"x": 50.0, "y": 40.0, "teammate": True, "actor": True},
        {"x": 98.0, "y": 42.0, "teammate": False},
        {"x": 119.0, "y": 40.0, "teammate": False, "keeper": True},
    ]
    out = compute_offside_margin(players)
    assert out["is_offside"] is True
    assert out["margin_meters"] > 0
    assert out["attacker_x"] == 100.0
