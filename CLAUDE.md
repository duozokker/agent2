@AGENTS.md

## Claude Code

Use `/brain-clone` for new domain expert agents. It should produce agents that
look more like `agents/procurement-compliance-officer` than `example-agent`.

Keep this file short. Project-wide rules live in `AGENTS.md`; detailed framework
context lives in `llms.txt`, `llms-full.txt`, and `docs/brain-clone-pattern.md`.

When editing skills, preserve the Brain Clone concept. Only update skills to
point at current canonical examples, runtime behavior, and docs.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill
tool. When in doubt, invoke the skill — a false positive is cheaper than an
ad-hoc answer that misses the structured workflow.

Key routing rules:
- New domain expert / "clone my brain" / "brain clone" → invoke `/brain-clone`
- New simple agent / "scaffold agent" / "add agent" → invoke `/creating-agents`
- Agent needs domain knowledge / documents / books → invoke `/building-domain-experts`
- Add knowledge collections / R2R / ingest PDFs → invoke `/adding-knowledge`
- Add pause/resume, approval, provider routing → invoke `/adding-capabilities`
- Agent errors / 500s / mock data / "agent broken" / "doesn't work" → invoke `/debugging-agents`
- Test agent / QA / "does this agent work" / health check → invoke `/agent-qa`
