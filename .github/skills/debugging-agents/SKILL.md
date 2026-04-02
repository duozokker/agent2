---
name: debugging-agents
description: Use when an Agent2 agent returns errors, 500s, mock data unexpectedly, fails to start, or behaves incorrectly — systematic diagnosis for framework issues, config problems, Docker issues, and runtime failures
---

# Debugging Agents

## Overview

Systematic diagnosis for Agent2 agent problems. Most issues are config, imports, or missing infrastructure — not code bugs.

## When to Activate

- Agent returns 500 errors or problem+json responses
- Agent returns mock data when you expect real LLM output
- Agent Docker container won't start or isn't healthy
- Agent doesn't find knowledge collections
- Agent output doesn't match expected schema
- Tests pass but Docker agent fails

## Diagnostic Flowchart

```
Agent not working?
  ├─ Returns mock data? → Check OPENROUTER_API_KEY (is it set? valid?)
  ├─ 500 error? → Check logs: docker compose logs <agent-name>
  ├─ Container unhealthy? → Check Dockerfile (config copy? PYTHONPATH?)
  ├─ 401/403? → Check API_BEARER_TOKEN matches between client and .env
  ├─ Knowledge search empty? → Is R2R running? (--profile full) Were docs ingested?
  ├─ Schema validation error? → Agent output doesn't match output_type. Check prompt.
  └─ Import error? → Check agent module structure (__init__.py, agent.py naming)
```

## Quick Diagnosis Commands

```bash
# 1. Is the container running and healthy?
docker compose ps <agent-name>

# 2. What do the logs say?
docker compose logs <agent-name> --tail=50

# 3. Can you hit the health endpoint?
curl http://localhost:<port>/health

# 4. Does mock mode work? (tests framework without LLM)
curl -X POST http://localhost:<port>/tasks?mode=sync \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"input":{"text":"test"}}'

# 5. Are tests passing?
uv run pytest tests/ -v --tb=short

# 6. Is the Docker Compose config valid?
docker compose config --quiet
```

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `_mock_reason: provider_auth_failed` | OPENROUTER_API_KEY is invalid | Get a fresh key from openrouter.ai/keys |
| Mock data returned, no error | OPENROUTER_API_KEY is empty | Set it in `.env` |
| `Could not import agent module` | Import path wrong in Docker | Check Dockerfile: `COPY agents/<name>/ ./agent/` and `PYTHONPATH=/app` |
| `config.yaml not found` | Config not copied in Dockerfile | Add `mkdir -p agents/<name> && cp agent/config.yaml agents/<name>/config.yaml` |
| `toolsets=None` error | Passing None instead of empty list | Use `toolsets=[]` not `toolsets=None` |
| Knowledge search returns nothing | R2R not running or docs not ingested | `docker compose --profile full up -d` then `python -m shared.ingest --all` |
| `ProblemError 422` | Input shape wrong | `input` must be a JSON object: `{"input": {"text": "..."}}` |
| Container exits immediately | Python import error | Run locally first: `uv run python -c "from agents.<name>.agent import agent"` |
| Schema validation retry loop | Agent output doesn't fit Pydantic model | Simplify schema, add clearer prompt instructions, check Field constraints |

## Debugging Locally vs Docker

**Local** (faster iteration):
```bash
uv run uvicorn agents.<name>.main:app --port 8000
```

**Docker** (production-like):
```bash
docker compose build <name>
docker compose up <name> redis -d
docker compose logs <name> -f
```

Always verify locally first, then Docker. Most Docker issues are path/copy problems, not code.
