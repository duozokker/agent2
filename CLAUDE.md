# Agent2

The production runtime for AI agents. PydanticAI + FastAPI + R2R + Langfuse + FastMCP.

See @llms.txt for the compact project map and @llms-full.txt for expanded framework context.

## Build & Test

```bash
# Install dependencies
uv sync --extra dev

# Run unit tests (39 tests, no Docker needed)
uv run pytest tests/ -v

# Core stack (Postgres, Redis, Langfuse, demo agents)
docker compose up -d

# Full stack (adds R2R, Docling, Temporal, Knowledge MCP)
docker compose --profile full up -d

# Rebuild a specific agent after code changes
docker compose build example-agent && docker compose up -d example-agent --no-deps
```

## Code Style

- Python 3.12+, type hints on all function signatures
- PydanticAI agents use `instructions=` (not `system_prompt=`) and `toolsets=` for MCP
- OpenRouter models: use `OpenAIChatModel` + `OpenRouterProvider` (not string shorthand)
- FastMCP tools: `@mcp.tool` decorator without parentheses
- Error responses: RFC 7807 `application/problem+json` via `ProblemError`
- Config: frozen dataclasses with `from_env()` classmethod, not pydantic-settings
- Imports: `from __future__ import annotations` in all shared/ modules

## Architecture Rules

- `shared/` is framework code — agents should never modify it
- Each agent is a separate Docker service with its own FastAPI app
- Agent code lives in `agents/<name>/` with: `agent.py`, `schemas.py`, `tools.py`, `config.yaml`, `main.py`
- `create_agent()` in `shared/runtime.py` is the only way to build agents
- `create_app()` in `shared/api.py` is the only way to build FastAPI apps
- Prompts are code-first by default; Langfuse is optional for iteration and observability
- Knowledge bases are R2R collections defined in `knowledge/collections.yaml`

## Key Patterns

- **Structured output**: Define a Pydantic `BaseModel`, pass as `output_type=` — PydanticAI retries on validation failure
- **MCP tools**: Pass `MCPServerStreamableHTTP` instances via `toolsets=` parameter
- **Mock mode**: When `OPENROUTER_API_KEY` is empty, agents use PydanticAI `"test"` model and API returns schema-compliant mock data
- **Task execution**: `POST /tasks?mode=sync` runs inline, `?mode=async` queues to Redis and returns task_id for polling
- **Pause/resume**: Accept `message_history` on input, return `_message_history` on output — host persists wherever it wants
- **Human approval**: Return `pending_actions`, host calls `POST /tasks/{task_id}/actions/execute`
- **Auth**: Bearer token via `Authorization` header, HMAC timing-safe comparison

## Testing

```bash
# Unit tests
uv run pytest tests/ -v

# Single test file
uv run pytest tests/test_shared/test_api.py -v

# Promptfoo evals (needs running agents + npm install -g promptfoo)
npx promptfoo eval -c tests/promptfoo/example-agent/eval.yaml
```

## Creating a New Agent

```bash
cp -r agents/_template agents/my-agent
# Edit: config.yaml (name, model, collections)
# Edit: schemas.py (output Pydantic model)
# Edit: agent.py (create_agent + tools)
# Edit: main.py (change create_app name)
# Edit: Dockerfile (change agent path)
# Add service to docker-compose.yml
```

## Common Gotchas

- Agent Dockerfiles must `mkdir -p agents/<name> && cp agent/config.yaml agents/<name>/config.yaml` for config discovery
- R2R needs `LITELLM_DROP_PARAMS=true` when using Cohere embeddings (Cohere doesn't accept dimensions param)
- Redis requires password auth: `redis://:${REDIS_AUTH}@redis:6379`
- Langfuse v3 requires ClickHouse + MinIO (not just Postgres)
- FastMCP `http_app(routes=...)` param doesn't exist in current version — use Starlette wrapper
- PydanticAI `toolsets=[]` (empty list) is safe, but `toolsets=None` may cause issues in some versions
