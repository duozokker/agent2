"""Tests for generic approval workflow primitives."""

from __future__ import annotations

from typing import Any

import pytest

from shared.approval_workflow import ApprovalWorkflow, ApprovalWorkflowError


class MemoryStore:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state

    async def get_run_state(self, run_id: str) -> dict[str, Any] | None:
        if self.state.get("task_id") == run_id:
            return self.state
        return None

    async def save_run_state(
        self,
        run_id: str,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        assert self.state["task_id"] == run_id
        if status is not None:
            self.state["status"] = status
        if result is not None:
            self.state["result"] = result


@pytest.mark.asyncio
async def test_execute_pending_action_updates_result() -> None:
    state = {
        "task_id": "task-1",
        "status": "completed",
        "result": {
            "pending_actions": [
                {
                    "action": "store_note",
                    "params": {"note": "approved"},
                    "description": "Store a note",
                }
            ]
        },
    }

    async def executor(action: dict[str, Any]) -> dict[str, Any]:
        return {"stored": action["params"]["note"]}

    workflow = ApprovalWorkflow(store=MemoryStore(state), action_executor=executor)
    result = await workflow.execute_pending_action("task-1", action="store_note")

    assert result["success"] is True
    assert state["result"]["pending_actions"] == []
    assert state["result"]["_executed_actions"][0]["result"]["stored"] == "approved"


@pytest.mark.asyncio
async def test_execute_pending_action_rejects_missing_action() -> None:
    state = {"task_id": "task-1", "status": "completed", "result": {"pending_actions": []}}
    workflow = ApprovalWorkflow(store=MemoryStore(state))

    with pytest.raises(ApprovalWorkflowError) as exc_info:
        await workflow.execute_pending_action("task-1", action="store_note")

    assert exc_info.value.status == 404


@pytest.mark.asyncio
async def test_execute_pending_action_rejects_ambiguous_action() -> None:
    state = {
        "task_id": "task-1",
        "status": "completed",
        "result": {
            "pending_actions": [
                {"action": "store_note", "params": {"note": "a"}},
                {"action": "store_note", "params": {"note": "b"}},
            ]
        },
    }
    workflow = ApprovalWorkflow(store=MemoryStore(state))

    with pytest.raises(ApprovalWorkflowError) as exc_info:
        await workflow.execute_pending_action("task-1", action="store_note")

    assert exc_info.value.status == 409
