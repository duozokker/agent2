# Deployment and Scaling

## Local development

### Core framework stack

```bash
docker compose up -d
```

This is the fast default loop for framework work and most agent development.

### Full platform stack

```bash
docker compose --profile full up -d
```

Use this when you need RAG, OCR, Knowledge MCP, or Temporal services.

## Container deployment model

Each agent is a standalone FastAPI service. That makes the framework portable:

- Docker Compose locally
- Railway services
- ECS / Nomad / Kubernetes later if needed

The important point is that Agent2 does not rely on a single monolith process.

## Scaling guidance

### Scale agents horizontally

Run more replicas for agents with high request volume.

### Prefer async for long jobs

Use `mode=async` for work that should not block the caller.

### Externalize state

The framework already externalizes task state. Hosts should also externalize conversation history and approval state into durable stores that fit their product architecture.

### Keep provider policy explicit

Provider routing has real cost implications. Treat `provider_order` and `provider_policy` as part of deployment configuration, not as ad-hoc prompt code.

## Railway mapping

Typical Railway setup:

- Postgres service
- Redis service
- one service per agent
- optional Langfuse services
- optional R2R / Knowledge MCP services

This mirrors the Docker topology and keeps migration straightforward.
