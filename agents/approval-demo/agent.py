"""Framework demo for approval-enabled agent runs."""

from __future__ import annotations

from typing import Any

from shared.action_executor import ActionRegistry
from shared.runtime import create_agent

from .schemas import ApprovalDemoResult

output_type = ApprovalDemoResult

agent = create_agent(
    name="approval-demo",
    output_type=ApprovalDemoResult,
    instructions=(
        "You are a framework demo agent. Return a structured summary and use "
        "pending_actions when a host should approve side effects."
    ),
)

action_registry = ActionRegistry()


async def _store_note(action: dict[str, Any]) -> dict[str, Any]:
    note = str(action.get("params", {}).get("note", ""))
    return {"stored": note or "approved"}


action_registry.register("store_note", _store_note)


async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
    return await action_registry.execute(action)


def mock_result(input_data: dict[str, Any]) -> dict[str, Any]:
    if input_data.get("require_approval"):
        note = str(input_data.get("note", "approved by operator"))
        return {
            "status": "needs_approval",
            "message": "The run produced a pending action that should be approved by the host.",
            "confidence": 0.92,
            "pending_actions": [
                {
                    "action": "store_note",
                    "params": {"note": note},
                    "description": "Store the operator note in the host system.",
                }
            ],
        }

    return {
        "status": "completed",
        "message": "No approval required for this run.",
        "confidence": 0.98,
        "pending_actions": [],
    }
