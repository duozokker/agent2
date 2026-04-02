# Agent2 — Production Runtime for AI Agents

## What this repo is
Agent2 is a framework for building production AI agents with typed HTTP APIs.
PydanticAI handles the agent loop. Agent2 handles everything else: API, auth,
pause/resume, approvals, provider routing, knowledge search.

## Key patterns
- Agents live in agents/<name>/ with: schemas.py, agent.py, tools.py, config.yaml, main.py
- create_agent() from shared/runtime.py is the ONLY way to build agents
- create_app() from shared/api.py is the ONLY way to build FastAPI apps
- Use instructions= (not system_prompt=) for agent prompts
- Use toolsets= for MCP server connections
- Output schemas are Pydantic BaseModel classes passed as output_type=

## Code style
- Python 3.12+, type hints on all signatures
- from __future__ import annotations in all shared/ modules
- RFC 7807 error responses via ProblemError
- Config uses frozen dataclasses with from_env(), not pydantic-settings
- OpenRouter models: OpenAIChatModel + OpenRouterProvider

## Architecture rules
- shared/ is framework code — never modify it for agent-specific logic
- Each agent is a separate Docker service
- Prompts are code-first; Langfuse is optional for observability
- Knowledge is in R2R, accessed via Knowledge MCP

## Testing
- uv run pytest tests/ -v (unit tests, no Docker needed)
- Docker: docker compose up -d && curl localhost:8001/health

## Creating a new agent
1. cp -r agents/_template agents/my-agent
2. Edit schemas.py (Pydantic output model)
3. Edit agent.py (create_agent + tools)
4. Edit config.yaml (name, model, collections)
5. Edit main.py (create_app call)
6. Add to docker-compose.yml
