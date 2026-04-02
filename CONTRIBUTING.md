# Contributing to Agent2

Thanks for your interest in contributing to Agent2!

## Development Setup

```bash
git clone https://github.com/duozokker/agent2.git
cd agent2
cp .env.example .env
uv sync --extra dev
uv run pytest tests/ -v
```

## Making Changes

1. Fork the repo and create a feature branch
2. Make your changes in the feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `uv run pytest tests/ -v`
5. Ensure code passes lint: `uv run ruff check shared/ agents/ tests/`
6. Submit a pull request

## Code Style

- Python 3.12+, type hints on all function signatures
- `from __future__ import annotations` in all `shared/` modules
- PydanticAI agents use `instructions=` (not `system_prompt=`)
- Error responses use RFC 7807 `application/problem+json`
- Config uses frozen dataclasses with `from_env()`, not pydantic-settings

## Architecture Rules

- `shared/` is framework code — agents should never modify it
- Each agent is a separate service with its own FastAPI app
- `create_agent()` is the only way to build agents
- `create_app()` is the only way to build FastAPI apps
- Prompts are code-first; Langfuse is optional

## Creating a New Agent

```bash
cp -r agents/_template agents/my-agent
# Edit config.yaml, schemas.py, agent.py, main.py, Dockerfile
# Add service to docker-compose.yml
```

See [docs/creating-agents.md](./docs/creating-agents.md) for the full guide.

## Reporting Issues

Use GitHub Issues. Include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Agent2 version and Python version
