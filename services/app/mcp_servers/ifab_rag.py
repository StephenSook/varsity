"""IFAB-RAG MCP server: exposes the Law retriever as a federated MCP tool.

Registered with the Context Forge gateway (``POST /gateways``) so the Granite
coordinator can call ``retrieve_law`` over MCP. Run standalone (SSE on :8001):

    python -m app.mcp_servers.ifab_rag
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.rag.retriever import LawRetriever

mcp = FastMCP("ifab-rag", host="0.0.0.0", port=8001, stateless_http=True, json_response=True)
_retriever = LawRetriever()


def retrieve_law(query: str, use_embeddings: bool = False) -> dict:
    """Retrieve the governing IFAB Law (number, title, exact text) for a query.

    Defaults to the deterministic keyword path so the federated tool is fast and
    needs no network; pass ``use_embeddings=True`` to re-rank with Granite embeddings.
    """
    chunk = _retriever.retrieve(query, use_embeddings=use_embeddings)
    return {"law": chunk.law, "title": chunk.title, "text": chunk.text}


mcp.tool()(retrieve_law)


if __name__ == "__main__":
    mcp.run(transport="sse")
