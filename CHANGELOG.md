# Changelog

All notable changes to Agent2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.4.0] - 2026-04-30

### Added
- Operational learnings system (`shared/learnings.py`): auto-logs low-confidence
  results, clarification patterns, and rejections after each agent run. The 3
  most recent learnings are injected into the next run's prompt.
- `/agent-qa` skill for end-to-end testing of deployed agents with schema
  validation and health reporting.
- Skill routing rules in `CLAUDE.md` for proactive skill invocation.
- `scripts/sync-skills.sh` to keep all 5 host directories (.claude, .agents,
  .codex, .gemini, .github) in sync from a single canonical source.
- Brain Clone SKILL.md: anti-sycophancy rules, forcing questions with pushback
  pattern tables, Phase 2.5 (Premise Challenge), Phase 6.5 (Scope Decision),
  Phase 7.5 (Architecture Review), agent quality rating (8 dimensions, /80),
  agent slop detection (10 anti-patterns), interview session persistence, and
  completion status protocol.

### Changed
- CLI interview prompt now loads dynamically from SKILL.md instead of
  maintaining a hardcoded copy. SKILL.md is the single source of truth.
- Phase labels updated from "X/6" to "X/8" including half-phases.
- `_detect_phase` and `_detect_phase_number` unified into shared keyword table.
- Generator produces 5 tests (complete, clarification, rejected, before_run,
  resume) instead of 1, and richer Promptfoo eval datasets from all example cases.
- Generator `mock_result` now covers all 3 outcomes including rejected.
- Generator `before_run` always sets `_instructions` for learnings injection.
- Generator config.yaml adds `knowledge_mcp` capability when collections exist.

### Fixed
- Learnings read AND write are both gated behind `AGENT2_DISABLE_LEARNINGS`
  env var to prevent test pollution.
- Skills synced across all host directories (previously .codex/.gemini/.github
  were missing `scandal-market-agent-builder`).

## [0.3.0] - 2026-04-30

### Added
- First-class `agent2` CLI with setup, onboard, doctor, list, run, serve, and
  publish-check commands.
- Static installer scripts for macOS/Linux and Windows.
- Agentic Brain Clone onboarding harness using validated `AgentSpec` objects and
  deterministic templates.
- Central `agent2.yaml` framework configuration for default model, provider
  policy, stack profile, telemetry, and framework ports.
- Generated-agent fixture and tests for onboarding without LLM calls.

### Changed
- Normal agent configs now use `model: ""` and resolve through global framework
  config.
- Docker agent images copy `agent2.yaml` so global config is available in
  containers.

## [0.2.0] - 2026-04-28

### Added
- Full Brain Clone flagship agent: `procurement-compliance-officer`.
- Public market research example agents: `scandal-market-finder`, `market-research-desk`, and `cultural-hype-analyst`.
- Interview evaluation example agent.
- Brain Clone and Sachbearbeiter pattern documentation.
- Procurement knowledge collections, seed books, and Promptfoo evals.
- `.agents` skill tree for AI coding tools that read AgentSkills-compatible skills.

### Changed
- Runtime now supports per-run `_toolsets` returned from `before_run()`.
- Brain Clone skills now use the Sachbearbeiter Chain-of-Thought pattern as the canonical agent design.
- `AGENTS.md`, `CLAUDE.md`, `llms.txt`, and `llms-full.txt` now orient AI coding agents toward the Agent2 vision and flagship examples.
- README and framework docs now distinguish primitive demos from full domain-expert examples.

### Fixed
- Runtime-only `_instructions`, `_toolsets`, and `message_history` are stripped from user prompt payloads.
- Knowledge MCP toolsets can be created fresh per request to avoid shared async cancel-scope issues.

## [0.1.0] - 2026-04-01

### Added
- Core framework: `create_agent()` and `create_app()`
- Typed outputs via Pydantic `output_type` with automatic retries
- Sync and async task execution (`POST /tasks?mode=sync|async`)
- Pause/resume with serialized message history
- Human-in-the-loop approval workflows with `pending_actions`
- Provider routing via `provider_order` and `provider_policy`
- Tool interception and collection scoping via tool policies
- Mock mode for development without LLM keys
- RFC 7807 error responses
- Bearer token auth with timing-safe comparison and rate limiting
- `before_run` and `after_run` hooks
- Knowledge MCP server wrapping R2R hybrid search
- Example agents: example-agent, support-ticket, code-review, invoice
- Framework demos: approval-demo, resume-demo, provider-policy-demo, scoped-tools-demo
- Default and full Docker Compose stack profiles
- Promptfoo evaluation suite integration
- 39 unit tests covering framework primitives
- LLM-friendly documentation (llms.txt, llms-full.txt, AGENTS.md)
