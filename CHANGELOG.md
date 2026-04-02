# Changelog

All notable changes to Agent2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

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
