# Capabilities

Capabilities are optional framework features that products can turn on per agent.

They are intentionally generic. The framework provides primitives, not product-specific workflows.

## Current capability patterns

### `resume`

Use when an agent needs multi-turn continuity.

Framework support:

- `input.message_history`
- returned `_message_history`
- helper serialization in [`shared/message_history.py`](../shared/message_history.py)

### `approval_workflow`

Use when an agent can propose side effects that need approval.

Framework support:

- `pending_actions`
- `POST /tasks/{task_id}/actions/execute`
- [`shared/approval_workflow.py`](../shared/approval_workflow.py)

### `provider_policy`

Use when provider affinity matters for cost or prompt-cache behavior.

Framework support:

- `provider_order`
- `provider_policy`
- OpenRouter model settings wiring in `create_agent()`

### `scoped_tools`

Use when tool calls need request-scoped constraints.

Framework support:

- tool policies
- policy composition
- collection scoping helper

### `knowledge_mcp`

Use when an agent should search shared knowledge collections.

Framework support:

- Knowledge MCP service
- collection metadata in `knowledge/collections.yaml`
- optional tool scoping

## Capability metadata

Agent config advertises capabilities through:

```yaml
capabilities:
  - resume
  - approval_workflow
```

This keeps hosts, demos, and docs aligned without hardwiring every feature into every agent.
