# Agent2

![Agent2](./agent2-logo-banner.jpg)

**The production runtime for AI agents. Schema in, API out.**

You define a Pydantic schema, tools, and a prompt. Agent2 gives you a typed HTTP backend with auth, pause/resume, human approval, knowledge search, and provider routing — ready to deploy.

```
Your code:    schema + tools + prompt           (~50 LOC)
Agent2:       API + auth + queue + retry + resume + approval + knowledge + tracing
```

---

## Why Agent2 exists

The models are smart enough. Claude, Gemini, GPT — they reason, use tools, follow instructions. **The hard part isn't making agents think. It's making them work in production.**

"Work" means:

- **Typed outputs** — not "here's some JSON, good luck", but Pydantic-validated structured data with automatic retries on schema violations
- **Pause and resume** — agents that can ask a human a question, wait days for the answer, and pick up exactly where they left off
- **Human approval** — agents that propose side effects and wait for a human to say "yes" before executing
- **Provider routing** — keeping prompt caches warm across tool-call rounds instead of bouncing between providers and paying 10x
- **A real API** — auth, rate limiting, async queuing, RFC 7807 errors, health checks — production basics that every agent needs but nobody wants to build

Agent2 solves this. One `docker compose up`, one `create_agent()` call, and your agent is a production backend service.

---

## How it works

```text
Your product
  schemas + tools + prompt + host persistence
         │
         ▼
Agent2 framework
  create_agent() → create_app() → task API + auth + errors
  message history · approval workflow · provider policy · tool policies
         │
         ▼
Optional capabilities
  Knowledge MCP · R2R · OCR · Langfuse · Promptfoo
```

Every agent is a regular Python module in `agents/<name>/`:

| File | Purpose |
|---|---|
| `schemas.py` | Your Pydantic output model — the contract the framework enforces |
| `agent.py` | `create_agent()` call + tool registration |
| `tools.py` | Domain logic your agent can call |
| `config.yaml` | Model, timeout, collections, provider policy |
| `main.py` | `create_app()` — one line, full HTTP API |

Every agent exposes the same API:

```
GET  /health
POST /tasks?mode=sync          → run inline, return typed result
POST /tasks?mode=async         → queue task, return task_id
GET  /tasks/{task_id}          → poll status and result
POST /tasks/{task_id}/actions/execute  → approve a pending action
```

---

## Quick start

### Prerequisites

- Docker Desktop
- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Optional: [OpenRouter API key](https://openrouter.ai/keys) (works in mock mode without one)

### 1. Clone and run tests

```bash
git clone https://github.com/duozokker/agent2.git
cd agent2
cp .env.example .env
uv sync --extra dev
uv run pytest tests/ -v    # 39 tests, no Docker needed
```

### 2. Start the stack

```bash
docker compose up -d
```

### 3. Send your first request

```bash
curl -X POST http://localhost:8001/tasks?mode=sync \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"input":{"text":"Summarize why typed outputs matter for agents."}}'
```

You get back validated, structured JSON — not freeform text.

---

## Feature matrix

| Feature | What it does | Demo agent | Docs |
|---|---|---|---|
| **Typed outputs** | Pydantic model as `output_type`, auto-retry on validation failure | [support-ticket](./agents/support-ticket) | [Creating Agents](./docs/creating-agents.md) |
| **Sync + async execution** | `mode=sync` for inline, `mode=async` for queued work with polling | [invoice](./agents/invoice) | [Getting Started](./docs/getting-started.md) |
| **Pause / resume** | Serialized `message_history` for multi-turn conversations | [resume-demo](./agents/resume-demo) | [Resume](./docs/resume-conversations.md) |
| **Human approval** | `pending_actions` + host-driven execution | [approval-demo](./agents/approval-demo) | [Approvals](./docs/approvals.md) |
| **Provider routing** | `provider_order` + `provider_policy` for cache-aware routing | [provider-policy-demo](./agents/provider-policy-demo) | [Provider Policy](./docs/provider-policy.md) |
| **Tool scoping** | Per-run tool interception and collection filtering | [scoped-tools-demo](./agents/scoped-tools-demo) | [Capabilities](./docs/capabilities.md) |
| **Knowledge search** | R2R + FastMCP for shared document collections | [rag-test](./agents/rag-test) | [Knowledge](./docs/knowledge-management.md) |
| **Observability** | Langfuse traces, prompt management, cost tracking | — | [Observability](./docs/observability.md) |
| **Mock mode** | Full API without an LLM key — returns schema-compliant mock data | [code-review](./agents/code-review) | [Getting Started](./docs/getting-started.md) |

---

## Build your first agent

### 1. Copy the template

```bash
cp -r agents/_template agents/my-agent
```

### 2. Define your output

```python
# agents/my-agent/schemas.py
from pydantic import BaseModel, Field

class InvoiceSummary(BaseModel):
    vendor: str = Field(description="Vendor name")
    total: float = Field(gt=0, description="Total amount in EUR")
    account_code: str = Field(description="Suggested booking account")
    confidence: float = Field(ge=0.0, le=1.0)
```

### 3. Create the agent

```python
# agents/my-agent/agent.py
from shared.runtime import create_agent
from .schemas import InvoiceSummary

agent = create_agent(
    name="my-agent",
    output_type=InvoiceSummary,
    instructions="You are an expert accountant. Extract invoice data into the declared schema.",
)

@agent.tool_plain
def lookup_vendor(name: str) -> dict:
    """Check if this vendor exists in our database."""
    return {"known": True, "default_account": "6805"}
```

### 4. Expose the API

```python
# agents/my-agent/main.py
from shared.api import create_app
app = create_app("my-agent")
```

That's it. Your agent now has a production HTTP API with auth, rate limiting, structured output, async execution, and error handling.

---

## Why not X?

| Alternative | What it solves | What Agent2 adds |
|---|---|---|
| **PydanticAI alone** | Agent loop, structured output, tool calls | The production runtime: HTTP API, auth, async queue, pause/resume, approvals, provider routing |
| **LangChain / LangServe** | Prompt orchestration, chain composition | Task-centric execution (not conversation-centric), typed output enforcement, approval workflows |
| **CrewAI / AutoGen** | Multi-agent coordination | Single-agent production deployment — one agent, one schema, one endpoint. Orchestrate multiple Agent2 services if you need multi-agent |
| **OpenClaw** | Personal AI agent on your laptop | Enterprise backend agents — HTTP-callable, multi-tenant, typed outputs, scalable on any container platform |
| **Building it yourself** | Full control | You skip writing ~3000 LOC of framework code: auth, error handling, async queue, message history serialization, approval workflow, provider routing, mock mode, dual layout detection |

---

## Stack

Agent2 stays close to the ecosystem instead of reinventing it:

| Layer | Technology | Why |
|---|---|---|
| Agent runtime | [PydanticAI](https://ai.pydantic.dev/) | Structured output, tool use, retries, model-agnostic |
| HTTP API | [FastAPI](https://fastapi.tiangolo.com/) | Auth, rate limiting, async, OpenAPI docs |
| LLM provider | [OpenRouter](https://openrouter.ai/) | Any model — Claude, Gemini, GPT, Llama — one API key |
| Knowledge search | [R2R](https://github.com/SciPhi-AI/R2R) + [FastMCP](https://github.com/jlowin/fastmcp) | Document ingestion, hybrid search, reranking via MCP |
| OCR | [Docling](https://github.com/docling-project/docling) | PDF extraction, table recognition, layout analysis |
| Observability | [Langfuse](https://langfuse.com/) | Traces, prompt registry, cost tracking, evals |
| Eval testing | [Promptfoo](https://promptfoo.dev/) | Pre-deploy regression testing for agent behavior |
| Task queue | Redis | Async task state, polling |
| Infra | Postgres, ClickHouse, MinIO | R2R storage, Langfuse backend |

---

## Default vs. full stack

**Default** (`docker compose up -d`) — fast developer loop:
- Postgres, Redis, Langfuse
- example-agent, support-ticket, code-review, invoice, approval-demo, resume-demo, provider-policy-demo

**Full** (`docker compose --profile full up -d`) — complete platform:
- Everything above + R2R, Docling, Temporal, Knowledge MCP
- rag-test, scoped-tools-demo

---

## Documentation

| Topic | Link |
|---|---|
| Architecture | [docs/architecture.md](./docs/architecture.md) |
| Getting Started | [docs/getting-started.md](./docs/getting-started.md) |
| Creating Agents | [docs/creating-agents.md](./docs/creating-agents.md) |
| Capabilities | [docs/capabilities.md](./docs/capabilities.md) |
| Resume and Conversations | [docs/resume-conversations.md](./docs/resume-conversations.md) |
| Approvals | [docs/approvals.md](./docs/approvals.md) |
| Provider Policy | [docs/provider-policy.md](./docs/provider-policy.md) |
| Knowledge Management | [docs/knowledge-management.md](./docs/knowledge-management.md) |
| Observability | [docs/observability.md](./docs/observability.md) |
| Deployment and Scaling | [docs/deployment.md](./docs/deployment.md) |
| When to use Agent2 | [docs/comparison.md](./docs/comparison.md) |

---

## AI-assisted development

Agent2 ships with built-in skills for AI coding tools. Open this repo in Claude Code, Cursor, Codex, or Gemini CLI and your agent already knows how to work with the framework.

| Skill | What it does | Trigger |
|---|---|---|
| **creating-agents** | Scaffolds a complete agent service | "new agent", "scaffold agent" |
| **building-domain-experts** | Patterns for knowledge-backed document processing agents | "expert agent", "document processing" |
| **adding-knowledge** | R2R collections, ingestion, per-tenant knowledge scoping | "add knowledge", "add books", "RAG" |
| **adding-capabilities** | Pause/resume, approvals, provider routing, tool scoping | "add resume", "add approval" |
| **debugging-agents** | Systematic diagnosis for framework issues | "agent doesn't work", "500 error" |

Skills follow the [open SKILL.md standard](https://agents.md/) and are available in `.claude/skills/`, `.codex/skills/`, `.gemini/skills/`, and `.github/skills/`.

---

## Design principles

- **Framework code lives in `shared/`.** Product logic lives in agent modules.
- **Capabilities are opt-in.** Pause/resume, approvals, knowledge, tool scoping — use what you need.
- **Prompts are code-first.** Langfuse is optional for iteration and observability, not a requirement.
- **Errors are RFC 7807.** Every failure returns `application/problem+json`.
- **No lock-in.** Standard Python, standard Docker, standard FastAPI. Deploy anywhere.

---

## Status

Agent2 provides production-tested runtime primitives that emerged from real enterprise work — processing millions of documents for German tax firms.

Current release: **v0.1.0** (pre-release, API stable for core features)

### What's here

- Typed agent creation with `create_agent()`
- Full HTTP API with `create_app()`
- Sync and async task execution
- Pause/resume with serialized message history
- Human-in-the-loop approval workflows
- Provider-aware execution with cache routing
- Tool interception and collection scoping
- Mock mode for development without LLM keys
- 39 unit tests covering framework primitives
- GitHub Actions CI with lint + test + Docker verify
- 5 built-in skills for AI coding tools (Claude Code, Codex, Gemini CLI, Copilot)

### Roadmap

- [ ] PyPI package (`pip install agent2`)
- [ ] Agent2 Cloud (managed hosting + dashboard)
- [ ] CLI for agent scaffolding
- [ ] Multi-agent orchestration primitives
- [ ] WebSocket streaming for long-running tasks
- [ ] Plugin system for community agent templates

---

## Built by Artesiana

Agent2 was born from production work at [Artesiana](https://artesiana.de), where we build AI agents for enterprise document processing. The framework has powered 4M+ processed documents and $200k+ in revenue since September 2025.

We're open-sourcing the core because we believe the production runtime for AI agents should be a shared foundation, not a proprietary moat.

---

## Built with Agent2

### MandantLink — Autonomous invoice processing for tax firms

[MandantLink](https://mandantlink.de) is the product that Agent2 was originally built for. It uses a single Sachbearbeiter agent that reads invoices via OCR, checks them against DATEV/GoBD accounting knowledge, asks the client clarifying questions when needed, and produces DATEV-ready booking entries.

The system processes invoices end-to-end: email or portal upload → OCR → knowledge-backed analysis → human approval → DATEV export. Built on Agent2's pause/resume, approval workflows, and knowledge search capabilities.

> **Have you built something with Agent2?** Open a PR to add your project here.

## License

[MIT](./LICENSE)
