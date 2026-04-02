"""
Knowledge MCP Server — wraps R2R hybrid search as MCP tools.

Runs as HTTP server on port 9090. Agents connect via MCPServerStreamableHTTP.
Calls R2R REST API at R2R_BASE_URL for actual search operations.
"""
from __future__ import annotations

import json
import os

import httpx
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

R2R_BASE_URL = os.environ.get("R2R_BASE_URL", "http://localhost:7272")

mcp = FastMCP("knowledge", instructions="Search and retrieve passages from knowledge bases. Use search() to find relevant information, get_passage() for full text.")


async def _resolve_collection_ids(names: list[str]) -> list[str]:
    """Resolve collection names to R2R collection IDs.

    Queries R2R's ``/v3/collections`` endpoint and maps each *name* to its
    UUID.  Names that are not found are passed through as-is (they might
    already be UUIDs).  On any network error the original list is returned
    unchanged so the caller can still attempt the search.
    """
    if not names:
        return []
    try:
        async with httpx.AsyncClient(base_url=R2R_BASE_URL, timeout=10.0) as client:
            resp = await client.get("/v3/collections", params={"limit": 100})
            resp.raise_for_status()
            all_collections = resp.json().get("results", [])
    except Exception:
        return names  # Fall back to passing names as-is

    name_to_id = {c.get("name", ""): c.get("id", "") for c in all_collections}
    resolved = []
    for name in names:
        if name in name_to_id:
            resolved.append(name_to_id[name])
        else:
            resolved.append(name)  # Pass as-is (might be an ID already)
    return resolved

@mcp.tool
async def search(query: str, collections: list[str] | None = None, limit: int = 5) -> str:
    """
    Hybrid search (semantic + keyword) across knowledge bases.

    Args:
        query: Search query (natural language or exact terms)
        collections: List of collection IDs to search in. If None, searches all.
        limit: Max results to return (1-20)
    """
    try:
        async with httpx.AsyncClient(base_url=R2R_BASE_URL, timeout=30.0) as client:
            body = {
                "query": query,
                "search_settings": {
                    "use_hybrid_search": True,
                    "limit": min(limit, 20),
                }
            }
            if collections:
                resolved_ids = await _resolve_collection_ids(collections)
                if resolved_ids:
                    body["search_settings"]["filters"] = {
                        "collection_ids": {"$in": resolved_ids}
                    }
            resp = await client.post("/v3/retrieval/search", json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        return f"Knowledge search unavailable: {exc}"
    except Exception as exc:
        return f"Knowledge search error: {exc}"

    # Format results for LLM consumption
    results = data.get("results", {}).get("chunk_search_results", [])
    if not results:
        return "No results found."

    formatted = []
    for i, r in enumerate(results, 1):
        text = r.get("text", "")[:2000]
        score = r.get("score", 0)
        chunk_id = r.get("id", "unknown")
        formatted.append(f"[{i}] (score: {score:.3f}, chunk: {chunk_id})\n{text}")

    return "\n\n---\n\n".join(formatted)


@mcp.tool
async def get_passage(chunk_id: str) -> str:
    """
    Retrieve the full text of a specific chunk by ID. Use after search() to get complete text for citation.

    Args:
        chunk_id: The chunk ID from a search result
    """
    try:
        async with httpx.AsyncClient(base_url=R2R_BASE_URL, timeout=30.0) as client:
            resp = await client.get(f"/v3/chunks/{chunk_id}")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        return f"Passage retrieval unavailable: {exc}"
    except Exception as exc:
        return f"Passage retrieval error: {exc}"

    result = data.get("results", {})
    text = result.get("text", "No text found")
    metadata = result.get("metadata", {})
    doc_id = result.get("document_id", "unknown")

    return f"Document: {doc_id}\nMetadata: {json.dumps(metadata, ensure_ascii=False)}\n\n{text}"


@mcp.tool
async def list_collections() -> str:
    """List all available knowledge base collections."""
    try:
        async with httpx.AsyncClient(base_url=R2R_BASE_URL, timeout=30.0) as client:
            resp = await client.get("/v3/collections", params={"limit": 100})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        return f"Collection listing unavailable: {exc}"
    except Exception as exc:
        return f"Collection listing error: {exc}"

    collections = data.get("results", [])
    if not collections:
        return "No collections found."

    lines = []
    for c in collections:
        name = c.get("name", "unnamed")
        desc = c.get("description", "")
        cid = c.get("id", "")
        count = c.get("document_count", 0)
        lines.append(f"- {name} (id: {cid}, docs: {count}): {desc}")

    return "\n".join(lines)


# Health endpoint for Docker healthcheck
async def health(request):
    return JSONResponse({"status": "ok", "service": "knowledge-mcp"})


# Build the ASGI app:
# 1. Create MCP HTTP app with stateless mode for scalability
# 2. Wrap in Starlette to add health endpoint alongside MCP
mcp_app = mcp.http_app(path="/mcp", stateless_http=True)

app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp_app),
    ],
    lifespan=mcp_app.lifespan,
)
