# Agent2

Production agent framework built on PydanticAI + FastAPI with optional R2R, Langfuse, FastMCP, and OCR capabilities.

See [`llms.txt`](./llms.txt) for the compact project map and [`llms-full.txt`](./llms-full.txt) for the expanded framework context.

## Build and test

```bash
uv sync --extra dev
uv run pytest tests/ -v

# Core stack
docker compose up -d

# Full stack with RAG and optional services
docker compose --profile full up -d
```

## Runtime rules

- `shared/` is framework code
- agents are built with `create_agent()` from [`shared/runtime.py`](./shared/runtime.py)
- apps are built with `create_app()` from [`shared/api.py`](./shared/api.py)
- prefer `instructions=` over `system_prompt=`
- `system_prompt=` remains a compatibility alias
- prompts are code-first; Langfuse is optional
- use `toolsets=` for MCP tool wiring
- errors must be RFC 7807 `application/problem+json`

## Framework primitives

- typed outputs through Pydantic models
- sync and async task execution
- `before_run` and `after_run` hooks
- serialized `message_history`
- generic `pending_actions`
- provider routing via `provider_order` and `provider_policy`
- optional scoped tool policies

## Project structure

- `shared/`: framework runtime
- `agents/`: reference agents and framework demos
- `knowledge/`: collection catalog and source documents
- `docs/`: public framework documentation
- `tests/`: unit and integration-oriented test coverage

## Current demos

- `example-agent`
- `support-ticket`
- `code-review`
- `invoice`
- `rag-test`
- `approval-demo`
- `resume-demo`
- `provider-policy-demo`
- `scoped-tools-demo`

## Common gotchas

- source layout and Docker layout both need to work for agent imports
- `input` on `/tasks` must be an object
- user-supplied `_instructions` are ignored unless a runtime hook injects them
- `toolsets=[]` is safe; avoid `toolsets=None`
- Knowledge MCP belongs to the `full` profile because it depends on R2R
