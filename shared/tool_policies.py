"""Helpers for tool interception and per-run tool call policies."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

ToolCaller = Callable[[str, dict[str, Any]], Awaitable[Any]]
ToolPolicy = Callable[[Any, ToolCaller, str, dict[str, Any]], Awaitable[Any]]


def compose_tool_policies(*policies: ToolPolicy) -> ToolPolicy:
    """Compose multiple tool policies into a single interceptor."""

    async def composed(ctx: Any, call_tool: ToolCaller, name: str, tool_args: dict[str, Any]) -> Any:
        async def invoke(index: int, current_name: str, current_args: dict[str, Any]) -> Any:
            if index >= len(policies):
                return await call_tool(current_name, current_args)

            async def next_call(next_name: str, next_args: dict[str, Any]) -> Any:
                return await invoke(index + 1, next_name, next_args)

            return await policies[index](ctx, next_call, current_name, current_args)

        return await invoke(0, name, dict(tool_args))

    return composed


def collection_scope_policy(collections_getter: Callable[[], list[str] | tuple[str, ...]]) -> ToolPolicy:
    """Scope search-like tool calls to a dynamic list of collection names."""

    async def policy(_ctx: Any, call_tool: ToolCaller, name: str, tool_args: dict[str, Any]) -> Any:
        scoped_args = dict(tool_args)
        if name == "search":
            active_collections = list(collections_getter())
            if active_collections:
                scoped_args["collections"] = active_collections
        return await call_tool(name, scoped_args)

    return policy
