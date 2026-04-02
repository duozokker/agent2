"""Framework demo for scoped MCP tool calls."""

from __future__ import annotations

import os
from contextvars import ContextVar

from pydantic_ai.mcp import MCPServerStreamableHTTP

from shared.runtime import create_agent
from shared.tool_policies import collection_scope_policy, compose_tool_policies

from .schemas import ScopedToolsDemoResult

output_type = ScopedToolsDemoResult

_ACTIVE_COLLECTIONS: ContextVar[tuple[str, ...]] = ContextVar(
    "scoped_tools_demo_collections",
    default=("test-knowledge",),
)

knowledge_server = MCPServerStreamableHTTP(
    os.environ.get("KNOWLEDGE_MCP_URL", "http://localhost:9090/mcp"),
    process_tool_call=compose_tool_policies(
        collection_scope_policy(lambda: list(_ACTIVE_COLLECTIONS.get()))
    ),
)

agent = create_agent(
    name="scoped-tools-demo",
    output_type=ScopedToolsDemoResult,
    instructions="You are a scoped tools demo agent.",
    toolsets=[knowledge_server],
)


def before_run(input_data: dict) -> dict:
    collections = input_data.get("collections")
    if isinstance(collections, list) and collections:
        _ACTIVE_COLLECTIONS.set(tuple(str(item) for item in collections if str(item).strip()))
    return input_data


def mock_result(input_data: dict) -> dict:
    collections = input_data.get("collections")
    if isinstance(collections, list) and collections:
        active_collections = [str(item) for item in collections if str(item).strip()]
    else:
        active_collections = list(_ACTIVE_COLLECTIONS.get())

    return {
        "status": "scoped",
        "active_collections": active_collections,
        "confidence": 0.94,
    }
