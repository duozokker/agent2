# Creating Agents

## Recommended: use `agent2 onboard`

The fastest way to create a domain expert agent is the Agent2 onboarding harness:

```bash
uv run agent2 setup
uv run agent2 onboard
```

It runs a Brain Clone interview to extract the expert's identity, knowledge
sources, decision patterns, tools, examples, and output contract. The LLM may
help synthesize the interview into an `AgentSpec`, but deterministic templates
write the files: schema, instructions, config, tools, tests, Promptfoo starter,
and Docker wiring.

For non-interactive generation:

```bash
uv run agent2 onboard --from-spec tests/fixtures/roofing-agent-spec.json --no-llm
```

The `/brain-clone` skill in Claude Code, Codex, Cursor, or another coding agent
is still the recommended way to refine the generated agent after onboarding.

For agents that need deep domain expertise (reading documents, checking regulations, asking clarifying questions), also see the `/building-domain-experts` skill.

Study [`agents/procurement-compliance-officer`](../agents/procurement-compliance-officer) before building a serious domain agent. It is the canonical in-repo example for the full Agent2 pattern: knowledge books, three outcomes, schema validators, per-run toolsets, memory, approval, resume, `after_run`, mock mode, tests, and evals.

The manual steps below cover the same process for cases where you want full control.

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

Use `model: ""` for normal agents. The framework resolves the model from
explicit runtime argument, then agent config, then `agent2.yaml`, then
`DEFAULT_MODEL`/built-in fallback.

```yaml
name: my-agent
description: "Summarizes invoices into typed accounting data"
model: ""
timeout_seconds: 120
max_retries: 3
collections: []
provider_order: []
provider_policy: {}
capabilities: []
```

Use:

- `collections` for knowledge access
- `provider_order` and `provider_policy` for cache-aware routing; `provider_order` disables OpenRouter fallbacks by default
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

For static MCP-based tools, pass `toolsets=[...]` into `create_agent()`. For
request-scoped MCP tools, `before_run()` may return `_toolsets`; the API runtime
passes them to `Agent.run(toolsets=...)` and keeps them out of the user prompt.

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
- add real source documents under `knowledge/books/<collection>/`
- add Promptfoo evals that prove the agent finds and applies the knowledge
