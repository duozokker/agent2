"""Tests for shared.tool_policies."""

from __future__ import annotations

import pytest

from shared.tool_policies import collection_scope_policy, compose_tool_policies


@pytest.mark.asyncio
async def test_collection_scope_policy_injects_collections_for_search() -> None:
    policy = collection_scope_policy(lambda: ["framework", "billing"])

    async def call_tool(name: str, args: dict[str, object]) -> dict[str, object]:
        return {"name": name, "args": args}

    result = await policy(None, call_tool, "search", {"query": "provider policy"})

    assert result["name"] == "search"
    assert result["args"]["collections"] == ["framework", "billing"]


@pytest.mark.asyncio
async def test_compose_tool_policies_applies_in_order() -> None:
    async def first(_ctx, call_tool, name: str, args: dict[str, object]):
        next_args = dict(args)
        next_args["first"] = True
        return await call_tool(name, next_args)

    async def second(_ctx, call_tool, name: str, args: dict[str, object]):
        next_args = dict(args)
        next_args["second"] = True
        return await call_tool(name, next_args)

    composed = compose_tool_policies(first, second)

    async def call_tool(name: str, args: dict[str, object]) -> dict[str, object]:
        return {"name": name, "args": args}

    result = await composed(None, call_tool, "search", {"query": "resume"})

    assert result["args"] == {"query": "resume", "first": True, "second": True}
