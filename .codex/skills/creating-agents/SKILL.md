---
name: creating-agents
description: Use when creating a new Agent2 agent, scaffolding a service, or when user says "new agent" or "add agent" — generates schema, tools, config, Dockerfile, and Docker Compose entry following Agent2 conventions
---

# Creating Agents

## Overview

Scaffold a complete Agent2 agent service. One agent = one schema, one API, one Docker service.

If the requested agent is a domain expert, regulated workflow, document reviewer,
compliance worker, or professional brain clone, use `brain-clone` first and
study `agents/procurement-compliance-officer`.

## When to Activate

- User says "create agent", "new agent", "scaffold agent", "add agent"
- User describes a use case that needs a new agent service
- User wants to add a new backend AI worker

## Steps

### 1. Gather Requirements

Ask the user:
1. **Name** (kebab-case, e.g. `support-ticket`)
2. **What it does** (one sentence)
3. **Output fields** (what the structured result should contain)
4. **Tools needed** (what the agent should be able to call)
5. **Knowledge needed?** (does it need to search documents?)

### 2. Generate Files

Create all files in `agents/<name>/`:

| File | What to put |
|---|---|
| `__init__.py` | Empty |
| `schemas.py` | Pydantic `BaseModel` with `Field()` descriptions. Use `Literal` for enums, validators for constraints. |
| `tools.py` | One function per tool. Include docstrings. Stub implementations. |
| `agent.py` | `create_agent()` with `instructions=` and `@agent.tool_plain` registrations |
| `config.yaml` | name, description, model (empty = use DEFAULT_MODEL), port, timeout, collections |
| `main.py` | `from shared.api import create_app; app = create_app("<name>")` |
| `Dockerfile` | Copy from `agents/example-agent/Dockerfile`, change agent paths |
| `tests/promptfoo/<name>/eval.yaml` | For domain agents, behavior-level evals |

### 3. Key Rules

```python
# agent.py — ALWAYS use instructions=, NEVER system_prompt=
agent = create_agent(
    name="my-agent",
    output_type=MySchema,
    instructions="You are...",
    toolsets=[knowledge_server] if needs_knowledge else [],
)

# Tools — ALWAYS @agent.tool_plain, delegate to tools.py
@agent.tool_plain
def my_tool(arg: str) -> dict:
    """Docstring is the tool description the LLM sees."""
    return tools.my_tool(arg)
```

### 4. Wire Into Docker Compose

Add a service block to `docker-compose.yml`. Use next available port. Copy environment block from `example-agent`.

### 5. Verify

```bash
uv run pytest tests/ -v                    # Unit tests still pass
docker compose build <name>                 # Image builds
docker compose up -d <name> redis           # Service starts
curl http://localhost:<port>/health          # Health check
curl -X POST http://localhost:<port>/tasks?mode=sync \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"input":{"text":"test"}}'            # Mock mode returns schema-valid JSON
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| Using `system_prompt=` | Use `instructions=` — system_prompt is a compat alias |
| Putting business logic in `shared/` | Business logic goes in `agents/<name>/tools.py` |
| Hardcoding model name | Leave `model: ""` in config, use `DEFAULT_MODEL` env var |
| Forgetting Dockerfile config copy | Must `mkdir -p agents/<name> && cp agent/config.yaml agents/<name>/config.yaml` |
| Using `toolsets=None` | Use `toolsets=[]` (empty list is safe, None can cause issues) |
| Building a domain expert from the tiny examples | Use `agents/procurement-compliance-officer` as the canonical full-pattern reference |
