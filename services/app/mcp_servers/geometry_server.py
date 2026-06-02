"""Match-geometry MCP server: offside margin from StatsBomb 360 freeze-frames.

Registered with the Context Forge gateway (``POST /gateways``). Run standalone
(SSE on :8002):

    python -m app.mcp_servers.geometry_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.geometry import FreezeFramePlayer, compute_offside

mcp = FastMCP("match-geometry", host="0.0.0.0", port=8002, stateless_http=True, json_response=True)


def compute_offside_margin(players: list[dict], ball_x: float | None = None) -> dict:
    """Compute the offside verdict and margin (meters) from freeze-frame players.

    Each player dict is ``{x, y, teammate, actor?, keeper?}``. Attack is always
    left-to-right (StatsBomb convention); the margin is the distance the most
    advanced attacker is ahead of the second-to-last opponent.
    """
    frame = [FreezeFramePlayer(**p) for p in players]
    res = compute_offside(frame, ball_x=ball_x)
    return {
        "is_offside": res.is_offside,
        "margin_meters": res.margin_meters,
        "offside_line_x": res.offside_line_x,
        "attacker_x": res.attacker_x,
    }


mcp.tool()(compute_offside_margin)


if __name__ == "__main__":
    mcp.run(transport="sse")
