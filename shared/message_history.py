"""PydanticAI message history serialization for pause/resume."""

from __future__ import annotations

from typing import Any


def serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Serialize PydanticAI messages into JSON-safe data."""
    from pydantic_core import to_jsonable_python

    return to_jsonable_python(messages)


def deserialize_messages(data: list[dict[str, Any]]) -> list[Any]:
    """Deserialize JSON-safe message history into PydanticAI message objects."""
    from pydantic_ai import ModelMessagesTypeAdapter

    return ModelMessagesTypeAdapter.validate_python(data)
