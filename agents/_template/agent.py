"""Template agent showing the framework extension points."""

from __future__ import annotations

from typing import Any

from shared.runtime import create_agent
from .schemas import MyAgentResult
from . import tools

# PydanticAI enforces ``output_type`` on every run.
agent = create_agent(
    name="my-agent",  # Match config.yaml
    output_type=MyAgentResult,
    instructions=(
        "Describe the job of your production agent here. Keep prompts code-first "
        "by default and switch to prompt_name=... only when you want Langfuse "
        "prompt management."
    ),
)


@agent.tool_plain
def example_tool(input_text: str) -> str:
    """Replace this with a real domain tool or MCP toolset."""
    return tools.example_tool(input_text)


def before_run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Optional hook for validation, scoping, or dynamic instructions."""
    if input_data.get("resume"):
        input_data["_instructions"] = "Continue the existing conversation and preserve context."
    return input_data


async def after_run(input_data: dict[str, Any], output: dict[str, Any]) -> None:
    """Optional hook for persistence, analytics, or host-side state updates."""
    output.setdefault("framework_notes", [])
    output["framework_notes"].append(
        {
            "hook": "after_run",
            "resume_requested": bool(input_data.get("resume")),
        }
    )
