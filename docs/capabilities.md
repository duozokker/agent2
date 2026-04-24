# Capabilities

Capabilities are the framework features that make domain expert agents work in production. A real expert does not just answer questions -- they remember context across conversations, propose actions that need approval, reference their professional knowledge base, and use specialized tools. Each capability below maps to one of those real-world patterns.

They are intentionally generic. The framework provides primitives, not product-specific workflows.

## Current capability patterns

### `resume`

Use when an agent needs multi-turn continuity -- the way a real expert asks clarifying questions before committing to a decision.

Framework support:

- `input.message_history`
- returned `_message_history`
- helper serialization in [`shared/message_history.py`](../shared/message_history.py)

### `approval_workflow`

Use when an agent proposes actions that need human sign-off -- the way an accountant flags unusual transactions for review.

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

Use when an agent needs to search professional reference materials -- regulations, manuals, institutional guides. Foundational to the expert cloning pattern.

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
