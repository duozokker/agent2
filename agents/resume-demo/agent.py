"""Framework demo for pause/resume using message history."""

from __future__ import annotations

from typing import Any

from pydantic_ai import ModelRequest, ModelResponse, TextPart, UserPromptPart

from shared.message_history import deserialize_messages, serialize_messages
from shared.runtime import create_agent

from .schemas import ResumeDemoResult

output_type = ResumeDemoResult

agent = create_agent(
    name="resume-demo",
    output_type=ResumeDemoResult,
    instructions="You are a pause/resume demo agent.",
)


def before_run(input_data: dict[str, Any]) -> dict[str, Any]:
    if input_data.get("message_history"):
        input_data["_instructions"] = (
            "Continue the existing conversation. Acknowledge that this is a resumed run."
        )
    return input_data


def mock_result(input_data: dict[str, Any]) -> dict[str, Any]:
    history = input_data.get("message_history") or []
    is_resume = bool(history)
    return {
        "status": "resumed" if is_resume else "fresh",
        "reply": "Resumed conversation successfully." if is_resume else "Started a new conversation.",
        "turns": len(history) + 1,
        "confidence": 0.96,
    }


async def after_run(input_data: dict[str, Any], output: dict[str, Any]) -> None:
    history_data = input_data.get("message_history") or []
    history = deserialize_messages(history_data) if history_data else []
    prompt = str(input_data.get("text") or input_data.get("question") or "resume-demo")
    response = str(output.get("reply", ""))
    history.extend(
        [
            ModelRequest(parts=[UserPromptPart(content=prompt)]),
            ModelResponse(parts=[TextPart(content=response)]),
        ]
    )
    output["_message_history"] = serialize_messages(history)
