# Changelog

All notable changes to Agent2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

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
