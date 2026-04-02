# Creating Agents

## 1. Copy the template

```bash
cp -r agents/_template agents/my-agent
```

## 2. Define the output schema

Your schema is the contract the framework enforces.

```python
from pydantic import BaseModel, Field


class InvoiceSummary(BaseModel):
    vendor: str = Field(description="Vendor name")
    amount: float = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)
```

## 3. Configure the agent

```yaml
name: my-agent
description: "Summarizes invoices into typed accounting data"
model: openrouter/anthropic/claude-sonnet-4
timeout_seconds: 120
max_retries: 3
collections: []
provider_order: []
provider_policy: {}
capabilities: []
```

Use:

- `collections` for knowledge access
- `provider_order` and `provider_policy` for cache-aware routing
- `capabilities` to declare optional framework features

## 4. Create the runtime

```python
from shared.runtime import create_agent
from .schemas import InvoiceSummary


agent = create_agent(
    name="my-agent",
    output_type=InvoiceSummary,
    instructions="You extract invoice data into the declared schema.",
)
```

`instructions=` is the preferred parameter. `system_prompt=` still works as a compatibility alias.

## 5. Add tools

```python
@agent.tool_plain
def lookup_vendor(name: str) -> dict[str, str]:
    return {"normalized_name": name.strip().title()}
```

For MCP-based tools, pass `toolsets=[...]` into `create_agent()`.

## 6. Use hooks when needed

### `before_run`

Use this to validate input, inject dynamic instructions, or set up request-scoped context.

```python
def before_run(input_data: dict[str, object]) -> dict[str, object]:
    if input_data.get("message_history"):
        input_data["_instructions"] = "Continue the prior conversation."
    return input_data
```

### `after_run`

Use this to persist state or annotate the response.

```python
async def after_run(input_data: dict[str, object], output: dict[str, object]) -> None:
    output["persisted"] = True
```

## 7. Expose the API

```python
from shared.api import create_app

app = create_app("my-agent")
```

## 8. Add Docker wiring

Create a service in [`docker-compose.yml`](../docker-compose.yml) using your agent Dockerfile.

## Common extension patterns

### Resume-capable agent

- accept `message_history`
- use `before_run()` to inject continuation instructions
- persist `_message_history` in the host

### Approval-capable agent

- return `pending_actions`
- implement `execute_action(action)` in the agent module or use a shared registry

### Knowledge-enabled agent

- add collection names to `config.yaml`
- attach a Knowledge MCP toolset
- optionally scope search at runtime through tool policies
