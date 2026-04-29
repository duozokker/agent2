"""
shared -- Framework library for Agent2.

Exports the most commonly needed symbols so agents can write::

    from shared import create_app, create_agent, Settings, AgentConfig

Imports that depend on heavy optional packages (pydantic-ai, fastapi, redis)
are deferred so that lightweight consumers (e.g. ``shared.config``) work
without those packages installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# These modules only depend on stdlib + PyYAML and are always safe to import.
from shared.config import (
    AgentConfig,
    FrameworkConfig,
    Settings,
    load_agent_config,
    load_collection_catalog,
    load_collections_for_agent,
    load_framework_config,
)
from shared.errors import ProblemError
from shared.message_history import deserialize_messages, serialize_messages

if TYPE_CHECKING:
    # Provide type information to editors without importing at runtime.
    from shared.api import create_app as create_app
    from shared.runtime import create_agent as create_agent


def __getattr__(name: str):
    """Lazy-import heavy symbols on first access."""
    if name == "create_app":
        from shared.api import create_app
        return create_app
    if name == "create_agent":
        from shared.runtime import create_agent
        return create_agent
    raise AttributeError(f"module 'shared' has no attribute {name!r}")


__all__ = [
    "AgentConfig",
    "FrameworkConfig",
    "Settings",
    "load_agent_config",
    "load_framework_config",
    "load_collection_catalog",
    "load_collections_for_agent",
    "create_app",
    "create_agent",
    "ProblemError",
    "serialize_messages",
    "deserialize_messages",
]
