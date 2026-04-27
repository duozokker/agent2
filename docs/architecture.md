# Architecture

## System model

Agent2 turns domain experts into production AI agents by separating framework concerns from domain concerns.

The framework handles the production runtime -- API, auth, task execution, knowledge search, pause/resume, and approval workflows. Domain agents encode how a specific expert works -- their prompts, tools, knowledge bases, and judgment patterns.

### Framework concerns

- task API
- auth and rate limiting
- error normalization
- async execution and polling
- message history serialization
- approval workflow primitives
- provider routing policy
- tool interception
- knowledge search infrastructure

### Domain concerns

- expert instructions and decision patterns
- domain tools (OCR, validation, external APIs)
- knowledge collections (regulations, reference materials, institutional guides)
- persistence schema
- external integrations
- approval UI and operator workflows

## Layered view

```text
Host product
  HTTP clients, UI, persistence, business side effects
         |
         v
Agent module
  schemas.py + agent.py + tools.py + config.yaml
         |
         v
Framework core
  create_agent() + create_app() + worker/task store + auth/errors
         |
         v
Optional services
  Langfuse, R2R, Docling, Knowledge MCP, Promptfoo
```

## Request lifecycle

### Sync run

1. Client sends `POST /tasks?mode=sync`
2. `shared/api.py` validates the body and enforces auth
3. The runtime loads the agent module from Docker layout or source layout
4. Optional `message_history` is deserialized
5. Optional `before_run()` mutates validated input, injects `_instructions`, and
   may provide per-run `_toolsets`
6. Runtime-only control fields are stripped from the user prompt
7. PydanticAI executes the run
8. Output is validated against the declared schema
9. `_message_history` is serialized back into the result
10. Optional `after_run()` persists or annotates output
11. API returns a typed result

### Async run

1. Client sends `POST /tasks?mode=async`
2. API stores a pending task in the task store
3. Background execution processes the same runtime flow as sync mode
4. Client polls `GET /tasks/{task_id}`

## Pause and resume

Pause/resume is intentionally transport-level and product-neutral:

- host persists `_message_history`
- host sends it back as `input.message_history`
- the framework restores the PydanticAI conversation state

This avoids forcing one database or one conversation model on every product.

## Human-in-the-loop

Approval is also generic:

- agent returns `pending_actions`
- host decides when and how to approve
- API exposes `POST /tasks/{task_id}/actions/execute`
- `ApprovalWorkflow` updates the stored result and executed-action log

The framework does not assume an email workflow, a portal, or a specific side effect type.

## Provider policy

OpenRouter provider policy belongs in framework config because it changes runtime economics:

- `provider_order` pins preferred providers
- `provider_policy.allow_fallbacks` controls fallback behavior

When `provider_order` is set, fallbacks are disabled by default so repeated tool-call rounds stay on the same provider for prompt-cache reuse.

This matters when prompt caching or provider-specific billing makes repeated routing decisions expensive.

## Tool policies

Tool policies are middleware for tool calls. They are useful for:

- collection scoping
- tenant scoping
- request metadata injection
- audit decoration
- policy enforcement before external calls

The framework ships composition and collection helpers. Products can layer their own policies on top.

For MCP clients that must be request-scoped, agents can return `_toolsets` from
`before_run()`. The API runtime passes them into `Agent.run(toolsets=...)`.

## Infrastructure

### Default stack

Default Docker starts the core framework loop without the knowledge search infrastructure. Useful for agents that do not need domain knowledge bases.

### Full stack

The `full` profile adds the knowledge and document processing layer:

- R2R (search and retrieval over expert knowledge bases)
- Docling (OCR and document conversion)
- Temporal
- Temporal UI
- Knowledge MCP
- RAG-oriented demos
- full-pattern domain examples such as `procurement-compliance-officer`

For domain expert agents, the full stack is the recommended setup. The default stack is available for simpler agents or faster iteration cycles.
