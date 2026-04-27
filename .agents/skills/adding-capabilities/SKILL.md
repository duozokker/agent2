---
name: adding-capabilities
description: Use when adding pause/resume, human approval, provider routing, tool scoping, or knowledge search to an existing agent — covers all optional Agent2 framework capabilities with implementation patterns
---

# Adding Capabilities to Agents

## Overview

Agent2 capabilities are opt-in. Start with a simple agent (schema + tools + prompt), then add capabilities as your use case requires them.

## When to Activate

- User says "add resume", "add approval", "add knowledge", "add provider policy"
- Agent needs multi-turn conversations
- Agent needs human-in-the-loop before executing side effects
- Agent needs cost-optimized provider routing
- Agent needs per-request tool filtering

## Capability Quick Reference

| Capability | When You Need It | What It Adds |
|---|---|---|
| **Pause/Resume** | Multi-turn workflows, clarification loops | `message_history` serialization |
| **Approval Workflow** | Human must approve before side effects | `pending_actions` + execute endpoint |
| **Provider Policy** | Cost control, prompt cache optimization | `provider_order` in config |
| **Tool Scoping** | Per-tenant or per-request tool filtering | Tool policy in `before_run()` |
| **Knowledge Search** | Agent needs domain documents | R2R + Knowledge MCP via `toolsets=` |

## Pause/Resume

**Add when**: Agent needs to ask a question and wait for a human to answer before continuing.

### 1. Accept history in before_run

```python
def before_run(input_data: dict) -> dict:
    if input_data.get("message_history"):
        input_data["_instructions"] = (
            "Continue the conversation. Read the human's response and proceed."
        )
    return input_data
```

### 2. Persist history in after_run

The framework auto-serializes `_message_history` into the response. Your host product stores it wherever it wants (Redis, Postgres, Convex, etc.) and sends it back on the next call.

### 3. Advertise in config

```yaml
capabilities:
  - resume
```

## Approval Workflow

**Add when**: Agent proposes side effects (send email, update records, make payments) that need human sign-off.

### 1. Return pending_actions from agent output or mock_result

```python
def mock_result(input_data: dict) -> dict:
    return {
        "status": "needs_approval",
        "pending_actions": [
            {
                "action": "send_email",
                "params": {"to": "user@example.com", "body": "..."},
                "description": "Send follow-up email to the client.",
            }
        ],
    }
```

### 2. Implement execute_action

```python
from shared.action_executor import ActionRegistry

registry = ActionRegistry()

async def _send_email(action: dict) -> dict:
    # Actually send the email
    return {"sent": True}

registry.register("send_email", _send_email)

async def execute_action(action: dict) -> dict:
    return await registry.execute(action)
```

### 3. Host calls the execute endpoint

```bash
POST /tasks/{task_id}/actions/execute
{"action": "send_email"}
```

### 4. Advertise in config

```yaml
capabilities:
  - approval_workflow
```

## Provider Policy

**Add when**: You want to keep prompt caches warm across tool-call rounds (saves 10x on input costs with Claude).

```yaml
# agents/my-agent/config.yaml
provider_order:
  - anthropic     # Prefer Anthropic's API (prompt cache stays warm)
provider_policy:
  allow_fallbacks: true  # Fall back to other providers if Anthropic is down
```

## Tool Scoping

**Add when**: Different tenants or requests should have access to different tools/collections.

```python
from shared.tool_policies import compose_tool_policies, collection_scope_policy

# Scope all search() calls to the active tenant's collections
policy = collection_scope_policy(lambda: list(_ACTIVE_COLLECTIONS.get()))
```

Or write a custom policy:

```python
async def my_policy(ctx, call_tool, name, tool_args):
    if name == "dangerous_tool" and not user_is_admin:
        return {"error": "Not authorized"}
    return await call_tool(name, tool_args)
```

## Combining Capabilities

Real production agents often use multiple capabilities together:

```python
agent = create_agent(
    name="my-expert",
    output_type=ExpertResult,
    instructions=SYSTEM_PROMPT,
    toolsets=[knowledge_server],  # Knowledge
)

def before_run(input_data):
    # Resume capability
    if input_data.get("message_history"):
        input_data["_instructions"] = "Continue the case."
    # Tool scoping capability
    _ACTIVE_COLLECTIONS.set(tuple(input_data.get("packages", [])))
    return input_data

async def after_run(input_data, output):
    # Persist results, update external systems
    if output.get("confidence", 0) < 0.85:
        output["needs_review"] = True  # Escalation

async def execute_action(action):
    # Approval capability
    return await registry.execute(action)
```

For per-run MCP clients, `before_run()` can also return `_toolsets`; Agent2
passes them to `Agent.run(toolsets=...)`. Study
`agents/procurement-compliance-officer` for the combined pattern.

```yaml
# config.yaml
capabilities:
  - resume
  - approval_workflow
  - knowledge_mcp
provider_order:
  - anthropic
```
