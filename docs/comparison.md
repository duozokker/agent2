# When to use Agent2

Agent2 turns domain experts into production AI agents. Not just how they think -- how they work. The tools they use, the books they reference, the judgment calls they make.

This document is an honest comparison of Agent2 against alternatives. The goal is to help you decide whether Agent2 is the right tool for your problem -- and to tell you when it is not.

## Agent2 vs prompt wrappers

Many "AI agent" tools are thin wrappers around a system prompt and an API call. They give you a chatbot with a persona, but no real domain expertise.

Agent2 is different. A domain expert agent built with Agent2 has:

- **Knowledge bases** -- the actual reference materials the expert would consult (regulations, manuals, internal guides), searchable via R2R
- **Domain tools** -- OCR for reading documents, validation logic, external API integrations
- **Structured output** -- typed Pydantic models that enforce the shape of the expert's work product
- **Multi-turn judgment** -- pause/resume and clarifying questions, the way a real expert would handle ambiguity
- **Human approval** -- pending actions for decisions that need sign-off, matching real-world workflows

A prompt wrapper gives you "an AI that sounds like an accountant." Agent2 gives you an agent that reads invoices, checks them against DATEV/GoBD regulations, asks clarifying questions, and produces compliant booking entries.

## Agent2 vs building it yourself (PydanticAI + FastAPI)

You absolutely can build this yourself. PydanticAI handles the agent loop, FastAPI handles HTTP. These are excellent libraries and Agent2 uses them directly -- it does not wrap or abstract them away.

But once you go from "working agent in a script" to "production service that clones a domain expert", you will end up writing roughly 3,000 lines of framework code that Agent2 already provides:

- **Auth** with HMAC timing-safe token comparison and fixed-window rate limiting
- **RFC 7807** error responses (`application/problem+json`) for every failure path
- **Async task queue** with Redis-backed polling (`POST /tasks?mode=async`, `GET /tasks/{task_id}`)
- **Message history serialization** for pause/resume across multiple turns
- **Approval workflow** with pending actions and host-driven execution
- **Provider routing** via `provider_order` and `provider_policy` for prompt cache optimization
- **Mock mode** that returns schema-compliant responses when no API key is set
- **Dual layout detection** so the same code works in Docker and source checkouts
- **`before_run` / `after_run` hooks** for input enrichment and side effects
- **Structured output enforcement** with automatic retry on validation failure

### With Agent2: 3 files, ~30 lines

**schemas.py** -- define your output type:

```python
from pydantic import BaseModel, Field

class DocumentSummary(BaseModel):
    title: str = Field(description="A concise title for the document")
    summary: str = Field(description="2-3 sentence summary")
    key_points: list[str] = Field(description="3-5 key takeaways")
    word_count: int = Field(description="Approximate word count", ge=0)
    language: str = Field(description="Detected language (e.g., 'en', 'de')")
    confidence: float = Field(description="Confidence score 0.0-1.0", ge=0.0, le=1.0)
```

**agent.py** -- create the agent and register tools:

```python
from shared.runtime import create_agent
from .schemas import DocumentSummary

agent = create_agent(
    name="example-agent",
    output_type=DocumentSummary,
    system_prompt="You are a document analysis assistant. ...",
)

@agent.tool_plain
def count_words(text: str) -> int:
    return len(text.split())
```

**main.py** -- one line:

```python
from shared.api import create_app

app = create_app("example-agent")
```

That is it. You get `/health`, `/tasks` (sync and async), `/tasks/{task_id}`, and `/tasks/{task_id}/actions/execute` -- all with auth, error handling, rate limiting, and typed outputs.

### Without Agent2: you write all of this yourself

```python
# You need to build:
# - FastAPI app with lifespan management
# - Auth middleware with timing-safe comparison (hmac.compare_digest)
# - Fixed-window rate limiter (thread-safe, per-token)
# - RFC 7807 error handler for validation errors
# - RFC 7807 error handler for application errors
# - Task store (Redis or in-memory) with status tracking
# - Async task execution with background workers
# - Message history serialization (PydanticAI messages -> JSON -> back)
# - Approval workflow with pending action storage and execution
# - Agent module loader that works in both Docker and source layouts
# - Mock mode that generates schema-compliant responses
# - Config loader from YAML + environment variables
# - Provider routing for OpenRouter model selection
# - before_run / after_run hook dispatch
# - Health endpoint
# - Structured logging setup
```

None of this is hard. All of it is tedious, and all of it has subtle edge cases (timing-safe auth, message history round-tripping, dual layout imports). Agent2 exists so you do not have to solve these problems again for every agent you deploy.

## Agent2 vs LangChain / LangServe

LangChain and Agent2 operate at different layers.

**LangChain** solves prompt orchestration: chains, RAG pipelines, memory, document loaders, output parsers. It provides its own abstraction over LLMs.

**Agent2** solves production deployment: HTTP API, auth, task queuing, pause/resume, approval workflows. It uses PydanticAI directly for the agent loop -- no additional LLM abstraction layer.

| Concern | LangChain / LangServe | Agent2 |
|---|---|---|
| LLM abstraction | Own wrapper over providers | PydanticAI (typed, validated) |
| Serving | LangServe wraps chains as endpoints | Full production API with auth, async tasks |
| Approval workflows | Not provided | Built-in pending actions + host execution |
| Pause/resume | Memory modules (conversation-scoped) | Serialized message history (task-scoped) |
| Provider routing | LiteLLM integration | OpenRouter `provider_order` / `provider_policy` |
| Tool scoping | Not provided | Per-run tool policies and collection scoping |
| Output typing | Output parsers (string-based) | Pydantic models with retry on validation failure |

**Can you use both?** In theory, yes. You could use LangChain for complex RAG chains inside an agent tool, and serve the agent through Agent2 for the production runtime. In practice, Agent2's built-in R2R integration and MCP tool support cover most RAG use cases without needing LangChain.

## Agent2 vs CrewAI / AutoGen

CrewAI and AutoGen solve multi-agent coordination. Agent2 solves single-agent production deployment. These are fundamentally different problems.

**CrewAI**: role-based multi-agent framework with delegation, sequential and parallel task execution, and inter-agent communication. Agents collaborate on a shared goal within a single process.

**AutoGen**: conversation-based multi-agent framework where agents talk to each other in structured dialogue patterns. Designed for complex reasoning through multi-turn agent conversations.

**Agent2**: one agent, one schema, one HTTP endpoint. Each agent is a separate Docker service with its own typed contract.

| Concern | CrewAI / AutoGen | Agent2 |
|---|---|---|
| Agent count | Multiple agents per process | One agent per service |
| Coordination | Built-in delegation / conversation | Not provided (use HTTP between services) |
| Deployment | Single process | One Docker service per agent |
| Typed outputs | Varies | Pydantic models, enforced |
| HTTP API | Not provided | Full production API |
| Auth / rate limiting | Not provided | Built-in |
| Pause/resume | Not built-in | Built-in message history |

**Agent2's philosophy**: scale agents by running more services, not by adding agents to one process. If you need multi-agent orchestration, use CrewAI or AutoGen for the coordination layer, and consider hosting individual agents as Agent2 services if they need independent HTTP APIs, typed outputs, or approval workflows.

## Agent2 vs Open Interpreter

Open Interpreter gives AI a body on your laptop. Agent2 gives AI a body in your backend.

| Concern | Open Interpreter | Agent2 |
|---|---|---|
| Environment | Local, single-user, terminal/chat | Server, multi-tenant ready, HTTP API |
| Interface | Interactive REPL / chat | Programmatic REST endpoints |
| Output | Freeform text and side effects | Typed Pydantic models |
| Auth | Not applicable | Bearer token, HMAC, rate limiting |
| Use case | Personal automation, exploration | Products that serve customers |

Open Interpreter is great for personal automation and interactive exploration. Agent2 is built for backend services that need to be called by other systems, return structured data, and handle multiple concurrent users.

## Agent2 vs Agency Swarm

Agency Swarm focuses on production-grade multi-agent systems with deterministic communication flows. Agent2 focuses on single-agent production services with enterprise features.

| Concern | Agency Swarm | Agent2 |
|---|---|---|
| Agent topology | Explicit communication graphs | Independent HTTP services |
| Communication | Deterministic inter-agent messaging | HTTP calls between services |
| Production features | Agent communication, state management | Auth, async tasks, approvals, pause/resume |
| Tool management | Shared tool infrastructure | MCP-based tool integration with scoping |

Both frameworks are production-oriented, but they target different scales of agent complexity. Agency Swarm is the right choice when you need structured multi-agent communication. Agent2 is the right choice when you need individual agents deployed as robust HTTP services.

## When NOT to use Agent2

**If you just need a chatbot**: use PydanticAI directly. Agent2 adds HTTP infrastructure you do not need for a simple conversational interface.

**If you need multi-agent orchestration**: use CrewAI, AutoGen, or Agency Swarm. Agent2 does not provide inter-agent coordination. You can host individual agents with Agent2, but the orchestration layer needs to come from elsewhere.

**If you need a personal AI assistant**: use Open Interpreter or a similar tool. Agent2 is server-side infrastructure, not a desktop application.

**If your agent does not need an HTTP API**: Agent2's entire value proposition is the production HTTP layer. If you are running agents in scripts, notebooks, or CLI tools, PydanticAI alone is the better choice.

**If you are prototyping in a notebook**: just use PydanticAI. You can always move to Agent2 later when you need to deploy.

**If you want provider abstraction**: Agent2 routes through OpenRouter. If you need direct multi-provider abstraction with fallback chains across providers, LiteLLM or LangChain might be a better fit.

---

Agent2 is for the specific moment when you want to take a domain expert's knowledge and deploy it as a production backend service -- with knowledge search, typed outputs, auth, async execution, pause/resume, approval workflows, and scaling. If that is not your problem, there is probably a simpler tool for your use case.
