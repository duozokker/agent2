# Agent2

Agent2 turns domain experts into production AI agents. The goal is not to build
deterministic scripts with a thin prompt on top. The goal is to clone how a
professional works: their workspace, books, tools, memory, review process,
judgment calls, clarification loops, and final typed work product.

Read [`llms.txt`](./llms.txt) for the compact map and
[`llms-full.txt`](./llms-full.txt) for expanded framework context.

## Build and test

```bash
uv sync --extra dev
uv run pytest tests/ -v

# Agent2 v0.3 CLI
uv run agent2 setup --dry-run
uv run agent2 onboard --from-spec tests/fixtures/roofing-agent-spec.json --no-llm --overwrite
uv run agent2 doctor --json

# Core stack
docker compose up -d

# Full stack with RAG, Knowledge MCP, OCR, and full-pattern examples
docker compose --profile full up -d
```

## Agent2 mental model

- A domain agent is a professional at a desk, not a rules engine.
- The prompt teaches the expert's Sachbearbeiter Chain-of-Thought; books contain what the expert knows.
- Domain knowledge belongs in R2R knowledge collections, not hardcoded lookup
  tables or giant prompts.
- Every serious domain agent should have three mutually exclusive outcomes:
  complete/approved, needs_clarification, or rejected.
- Pydantic schemas are contracts. Use `model_validator` to prevent contradictory
  states such as approved plus rejection reason.
- Side effects are sandboxed. Agents propose `pending_actions`; hosts or humans
  execute them through the approval workflow.
- Multi-turn work resumes through `message_history`, not by reprocessing the
  case from scratch.

## Runtime rules

- `shared/` is framework code.
- Agent business logic lives in `agents/<name>/`.
- `agent2.yaml` is the global source of truth for default model, provider
  policy, stack profile, telemetry, and framework ports.
- Build agents with `create_agent()` from [`shared/runtime.py`](./shared/runtime.py).
- Build apps with `create_app()` from [`shared/api.py`](./shared/api.py).
- Use `agent2 setup` for local `.env`/`agent2.yaml` generation and `agent2
  onboard` for Brain Clone agent scaffolding before hand-editing files.
- Use `instructions=`, not `system_prompt=`, for new code.
- `system_prompt=` exists only as a compatibility alias.
- Use `toolsets=[]` when no MCP tools are attached.
- Use `before_run()` for dynamic `_instructions`, request-scoped knowledge
  collections, resume hints, input guards, and per-run `_toolsets`.
- Per-run `_toolsets` from `before_run()` are supported by the API runtime and
  passed to `Agent.run(toolsets=...)`; they are stripped from the user prompt.
- Model resolution order is explicit runtime argument, agent `config.yaml`,
  `agent2.yaml`, then env fallback.
- Errors must be RFC 7807 `application/problem+json`.

## Canonical examples

- [`agents/procurement-compliance-officer`](./agents/procurement-compliance-officer):
  full Agent2 flagship. It uses the Brain Clone pattern, Knowledge MCP,
  per-run scoped toolsets, workspace prompt, memory tools, three outcomes,
  schema validators, sandbox approvals, resume, `after_run`, mock mode, and
  Promptfoo evals.
- [`docs/reference-agents/sachbearbeiter-pattern.md`](./docs/reference-agents/sachbearbeiter-pattern.md):
  explains the production-proven Sachbearbeiter pattern: one expert handles a
  complete case from document intake through review, communication, and final
  structured output.
- `approval-demo`, `resume-demo`, `provider-policy-demo`, and
  `scoped-tools-demo` are framework primitive demos.
- `example-agent`, `support-ticket`, `code-review`, `invoice`, and `rag-test`
  are small reference demos, not the standard for full domain experts.

## Definition of done for new domain agents

A new serious Agent2 domain agent is not complete until it has:

- `schemas.py` with typed output, three outcomes, confidence, observable
  `reasoning`, `review_steps`, `pending_actions`, and `model_validator`.
- `agent.py` with identity, workspace/tool metaphors, Sachbearbeiter Chain-of-Thought,
  example cases, outcome rules, `before_run`, `after_run`, and `mock_result`.
- `tools.py` with domain-named tools. Tools return errors as data where the
  agent can recover.
- Knowledge collections in `knowledge/collections.yaml` and real seed documents
  under `knowledge/books/<collection>/`.
- Sandbox tools for side effects and an `execute_action()` handler.
- Docker Compose wiring and config `capabilities`.
- Focused tests for schema consistency, runtime hooks, and mock behavior.
- Promptfoo evals that test real domain behavior, not just JSON shape.

## Project structure

- `shared/`: framework runtime, API, auth, approvals, message history, tool
  policies, Knowledge MCP.
- `agents/`: agent services and demos.
- `knowledge/`: collection catalog and source documents.
- `docs/`: framework and pattern documentation.
- `tests/`: unit, integration-oriented, and eval support.

## AI-assisted development skills

Use these skills when working in Claude Code, Codex, Cursor, or similar tools:

- `/brain-clone`: recommended starting point for domain expert agents.
- `/creating-agents`: scaffolds an Agent2 service.
- `/building-domain-experts`: documents the professional-workspace pattern.
- `/adding-knowledge`: adds R2R collections and Knowledge MCP wiring.
- `/adding-capabilities`: adds resume, approval, provider policy, scoping, or
  knowledge search.
- `/debugging-agents`: systematic diagnosis for runtime/config/test issues.

When building a domain expert, start from `/brain-clone` and study
[`agents/procurement-compliance-officer`](./agents/procurement-compliance-officer).

## Common gotchas

- Source layout and Docker layout both need to work for agent imports.
- `input` on `/tasks` must be a JSON object.
- User-supplied `_instructions` and `_toolsets` are ignored unless a runtime hook
  injects them.
- `toolsets=[]` is safe; avoid `toolsets=None`.
- Knowledge MCP belongs to the `full` profile because it depends on R2R.
- If the agent makes wrong domain decisions, fix books, chunking, prompt, or
  evals first. Do not add hidden deterministic lookup tables as the default fix.
