# Agent2 Copilot Instructions

This is Agent2, a production runtime for AI agents built on PydanticAI and FastAPI.

## When writing agent code:
- Import create_agent from shared.runtime
- Import create_app from shared.api
- Define output schemas as Pydantic BaseModel with Field() descriptions
- Use @agent.tool_plain for tool registration
- Use instructions= parameter (not system_prompt=)

## When writing framework code (shared/):
- Always use from __future__ import annotations
- Errors must be RFC 7807 via ProblemError
- Config must use frozen dataclasses
- Type hints on all function signatures

## File structure for agents:
agents/<name>/
  __init__.py
  schemas.py    - Pydantic output model
  agent.py      - create_agent() + tool registration
  tools.py      - Domain logic functions
  config.yaml   - Agent configuration
  main.py       - create_app() entrypoint
  Dockerfile    - Docker build instructions
