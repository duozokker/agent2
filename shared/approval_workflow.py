"""Generic approval workflow for pending agent actions."""

from __future__ import annotations

import copy
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from shared.action_executor import execute_action

ActionExecutor = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ApprovalWorkflowError(Exception):
    """Structured workflow error for HTTP translation."""

    def __init__(self, *, status: int, title: str, detail: str) -> None:
        self.status = status
        self.title = title
        self.detail = detail
        super().__init__(detail)


class ApprovalStateStore(Protocol):
    """Persistence contract for approval-enabled runs."""

    async def get_run_state(self, run_id: str) -> dict[str, Any] | None: ...

    async def save_run_state(
        self,
        run_id: str,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None: ...


class TaskStoreApprovalStore:
    """Adapter for the existing task store interface."""

    def __init__(self, task_store: Any) -> None:
        self.task_store = task_store

    async def get_run_state(self, run_id: str) -> dict[str, Any] | None:
        task = await self.task_store.get_task(run_id)
        return task.to_dict() if task is not None else None

    async def save_run_state(
        self,
        run_id: str,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {}
        if status is not None:
            payload["status"] = status
        if result is not None:
            payload["result"] = result
        if payload:
            await self.task_store.update_task(run_id, **payload)


class ApprovalWorkflow:
    """Validate and execute pending actions for a run result."""

    def __init__(
        self,
        *,
        store: ApprovalStateStore,
        action_executor: ActionExecutor = execute_action,
    ) -> None:
        self.store = store
        self.action_executor = action_executor

    async def execute_pending_action(
        self,
        run_id: str,
        *,
        action: str,
        params: dict[str, Any] | None = None,
        index: int | None = None,
    ) -> dict[str, Any]:
        state = await self._get_state(run_id)
        result = self._get_result(state)
        pending_actions = self._get_pending_actions(result)
        action_index, pending_action = self._find_pending_action(
            pending_actions,
            action=action,
            params=params or {},
            index=index,
        )

        prepared_action = copy.deepcopy(pending_action)
        execution_result = await self.action_executor(prepared_action)
        if execution_result.get("error"):
            raise ApprovalWorkflowError(
                status=502,
                title="Action Execution Failed",
                detail=str(execution_result["error"]),
            )

        pending_actions.pop(action_index)
        result["pending_actions"] = pending_actions
        executed_actions = result.setdefault("_executed_actions", [])
        if isinstance(executed_actions, list):
            executed_actions.append(
                {
                    "action": action,
                    "params": prepared_action.get("params", {}),
                    "result": execution_result,
                }
            )

        status = str(prepared_action.get("status_on_success") or state.get("status") or "completed")
        await self.store.save_run_state(run_id, status=status, result=result)

        return {
            "success": True,
            "run_id": run_id,
            "action": action,
            "status": status,
            "result": execution_result,
        }

    async def _get_state(self, run_id: str) -> dict[str, Any]:
        state = await self.store.get_run_state(run_id)
        if state is None:
            raise ApprovalWorkflowError(
                status=404,
                title="Run Not Found",
                detail=f"Run '{run_id}' was not found or has expired.",
            )
        return state

    @staticmethod
    def _get_result(state: dict[str, Any]) -> dict[str, Any]:
        result = state.get("result")
        if not isinstance(result, dict):
            raise ApprovalWorkflowError(
                status=409,
                title="Result Missing",
                detail="Run result is missing or not approval-enabled.",
            )
        return copy.deepcopy(result)

    @staticmethod
    def _get_pending_actions(result: dict[str, Any]) -> list[dict[str, Any]]:
        raw_actions = result.get("pending_actions") or []
        if not isinstance(raw_actions, list):
            raise ApprovalWorkflowError(
                status=409,
                title="Pending Actions Invalid",
                detail="result.pending_actions must be a list.",
            )
        actions: list[dict[str, Any]] = []
        for item in raw_actions:
            if isinstance(item, dict):
                actions.append(copy.deepcopy(item))
        return actions

    @staticmethod
    def _find_pending_action(
        pending_actions: list[dict[str, Any]],
        *,
        action: str,
        params: dict[str, Any],
        index: int | None,
    ) -> tuple[int, dict[str, Any]]:
        if index is not None:
            if index < 0 or index >= len(pending_actions):
                raise ApprovalWorkflowError(
                    status=404,
                    title="Pending Action Not Found",
                    detail=f"Pending action index {index} is out of range.",
                )
            candidate = pending_actions[index]
            if candidate.get("action") != action:
                raise ApprovalWorkflowError(
                    status=409,
                    title="Pending Action Mismatch",
                    detail=f"Pending action at index {index} is not '{action}'.",
                )
            if params and candidate.get("params") != params:
                raise ApprovalWorkflowError(
                    status=409,
                    title="Pending Action Mismatch",
                    detail="Pending action params do not match the requested action.",
                )
            return index, candidate

        matches: list[tuple[int, dict[str, Any]]] = []
        for candidate_index, candidate in enumerate(pending_actions):
            if candidate.get("action") != action:
                continue
            if params and candidate.get("params") != params:
                continue
            matches.append((candidate_index, candidate))

        if not matches:
            raise ApprovalWorkflowError(
                status=404,
                title="Pending Action Not Found",
                detail=f"No pending '{action}' action exists for this run.",
            )
        if len(matches) > 1 and not params:
            raise ApprovalWorkflowError(
                status=409,
                title="Pending Action Ambiguous",
                detail="Multiple matching pending actions exist. Provide index or params.",
            )
        return matches[0]
