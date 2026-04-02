"""Tests for message history serialization."""

from __future__ import annotations

import json

from pydantic_ai import ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart

from shared.message_history import deserialize_messages, serialize_messages


def test_message_history_roundtrip_text() -> None:
    messages = [
        ModelRequest(parts=[UserPromptPart(content="Hello")]),
        ModelResponse(parts=[TextPart(content="Hi there!")]),
    ]

    serialized = serialize_messages(messages)
    deserialized = deserialize_messages(serialized)
    assert deserialized[0].parts[0].content == "Hello"
    assert deserialized[1].parts[0].content == "Hi there!"


def test_message_history_roundtrip_tool_calls() -> None:
    messages = [
        ModelRequest(parts=[UserPromptPart(content="Analyze this")]),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="lookup_vendor",
                    args={"name": "Example GmbH"},
                    tool_call_id="call-1",
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="lookup_vendor",
                    content='{"known": true}',
                    tool_call_id="call-1",
                )
            ]
        ),
    ]

    serialized = serialize_messages(messages)
    deserialized = deserialize_messages(serialized)
    assert deserialized[1].parts[0].tool_name == "lookup_vendor"
    assert deserialized[2].parts[0].tool_call_id == "call-1"


def test_message_history_is_json_safe() -> None:
    messages = [
        ModelRequest(parts=[UserPromptPart(content="Hallo äöü")]),
        ModelResponse(parts=[TextPart(content="Antwort")]),
    ]
    payload = serialize_messages(messages)
    json.loads(json.dumps(payload))
