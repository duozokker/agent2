"""Generic action execution primitives for human-in-the-loop workflows."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

ActionHandler = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]


class ActionRegistry:
    """In-memory action registry used by demos and host applications."""

    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, action: str, handler: ActionHandler) -> None:
        self._handlers[action] = handler

    def has_handler(self, action: str) -> bool:
        return action in self._handlers

    async def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        action_name = str(action.get("action", ""))
        if action_name not in self._handlers:
            return {"error": f"No action handler registered for '{action_name}'."}

        result = self._handlers[action_name](action)
        if inspect.isawaitable(result):
            return await result
        return result


default_action_registry = ActionRegistry()


async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
    """Execute an action via the default registry."""
    return await default_action_registry.execute(action)
