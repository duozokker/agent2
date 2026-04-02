# Approvals

## Goal

Some agents should not execute side effects immediately. They should propose them and let the host decide.

Agent2 models this with `pending_actions`.

## Result shape

```json
{
  "status": "needs_approval",
  "pending_actions": [
    {
      "action": "store_note",
      "params": {"note": "approved by operator"},
      "description": "Store the note in the host system."
    }
  ]
}
```

## Execution flow

1. agent returns `pending_actions`
2. host inspects them
3. host calls `POST /tasks/{task_id}/actions/execute`
4. framework validates and executes the action
5. framework removes it from `pending_actions`
6. framework appends `_executed_actions`

## Extensibility

Products can:

- implement `execute_action(action)` in the agent module
- use a shared `ActionRegistry`
- attach their own persistence behind the workflow store interface

The framework does not assume email, CRM, ERP, or any specific business domain.

## Example

See [`agents/approval-demo`](../agents/approval-demo).
