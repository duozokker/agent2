# Getting Started

Agent2 turns domain experts into production AI agents. This guide gets you from zero to a running agent in minutes.

## Prerequisites

- Docker Desktop
- Python 3.12+
- `uv`
- optional `OPENROUTER_API_KEY`

## Local setup

```bash
git clone https://github.com/duozokker/agent2.git
cd agent2
cp .env.example .env
uv sync --extra dev
uv run pytest tests/ -v
```

## Start the default framework stack

```bash
docker compose up -d
docker compose ps
```

The default stack is enough to explore:

- sync tasks
- async tasks
- pause/resume
- pending actions
- provider policy wiring

If `3000` is already occupied, run:

```bash
LANGFUSE_WEB_PORT=3001 docker compose up -d
```

## Start the full stack

```bash
docker compose --profile full up -d
docker compose ps
```

Use the `full` profile when you need:

- R2R-backed knowledge search
- Docling OCR
- Knowledge MCP
- Temporal services
- RAG and scoped-tool demos

## First requests

### Example agent

```bash
curl -X POST http://localhost:8001/tasks?mode=sync \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"input":{"text":"Explain structured output in one sentence."}}'
```

### Resume demo

```bash
curl -X POST http://localhost:8005/tasks?mode=sync \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"input":{"text":"Start a new thread"}}'
```

Take `_message_history` from the response and send it again:

```bash
curl -X POST http://localhost:8005/tasks?mode=sync \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"input":{"text":"Continue the thread","message_history":[...]}}'
```

### Approval demo

```bash
curl -X POST http://localhost:8004/tasks?mode=async \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"input":{"text":"Create a pending action","require_approval":true}}'
```

Poll the task, inspect `pending_actions`, then execute one:

```bash
curl -X POST http://localhost:8004/tasks/<task_id>/actions/execute \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"action":"store_note"}'
```

## Useful dashboards

- Langfuse: [http://localhost:3000](http://localhost:3000)
- Temporal UI: [http://localhost:8233](http://localhost:8233)
- R2R health: [http://localhost:7272/v3/health](http://localhost:7272/v3/health)

## Next steps

- [Creating Agents](./creating-agents.md) -- or use the `/brain-clone` skill for a guided interview
- [Knowledge Management](./knowledge-management.md) -- set up the expert's reference materials
- [Capabilities](./capabilities.md) -- add pause/resume, approvals, and more
- [Deployment and Scaling](./deployment.md)
