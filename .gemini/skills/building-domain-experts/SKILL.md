---
name: building-domain-experts
description: Use when building an agent that needs deep domain expertise — reads documents, checks them against professional knowledge, asks clarifying questions, and produces structured domain-specific output. Covers knowledge-backed agents, document processing, multi-turn workflows with human approval, and per-context knowledge scoping.
---

# Building Domain Expert Agents

## Overview

A domain expert agent is the most powerful pattern in Agent2. It combines: document reading (OCR), domain knowledge (R2R search), context-aware reasoning, human-in-the-loop, and structured output. Think: an experienced professional sitting at a desk with reference books, tools, and the ability to ask questions.

## When to Activate

- User wants an agent that processes documents against professional standards
- Agent needs to "look things up" in reference material before deciding
- Agent needs to ask clarifying questions and resume after human answers
- Agent must produce structured output that follows domain-specific rules
- Industries: legal, medical billing, accounting, compliance, insurance, HR, procurement

## The Domain Expert Pattern

```
Document arrives (PDF, email, text)
  → Agent reads it (OCR via Docling MCP or text input)
  → Agent checks context (who is this for? what rules apply?)
  → Agent searches knowledge (R2R via Knowledge MCP)
  → Agent decides: complete? or needs clarification?
  → If complete: structured result + confidence score
  → If incomplete: clarifying question → pause → human answers → resume
  → Human approves final result
```

## Architecture

### 1. The Schema — Your Domain Contract

Design the output schema around the **three possible outcomes** every domain expert faces:

```python
class ExpertResult(BaseModel):
    status: Literal["complete", "needs_clarification", "rejected"]
    # Domain-specific structured output
    findings: list[Finding] = Field(default_factory=list)
    # Clarification path
    question: ClarificationRequest | None = None
    # Rejection path
    rejection_reason: str | None = None
    # Always present
    reasoning: str  # The expert's thought process
    confidence: float = Field(ge=0.0, le=1.0)
    review_steps: list[str] = Field(default_factory=list)
```

Add a `@model_validator` that enforces consistency (e.g. findings required when complete, question required when needs_clarification).

### 2. The Prompt — Think Like the Expert

Write the system prompt as if you're describing how an experienced professional thinks:

- **Identity**: "You are a senior [role] with 20 years of experience..."
- **Workspace**: Describe the tools on their desk (knowledge search, databases, web)
- **Thinking process**: Step-by-step how they approach a case
- **Decision criteria**: When to complete, when to ask, when to reject
- **Examples**: 3-5 typical scenarios showing different outcomes

The prompt should NOT dictate specific answers. It should teach the agent HOW TO THINK about the domain.

### 3. Knowledge Packages — Books on the Shelf

Domain knowledge belongs in R2R collections, not in code:

```yaml
# knowledge/collections.yaml
collections:
  industry-standards:
    description: "Core standards and regulations"
    books_dir: books/standards/
  reference-material:
    description: "Textbooks, commentaries, guides"
    books_dir: books/reference/
```

**Key principle**: New rules or standards? Add a book, not a code change. The agent is smart enough to learn from documents.

**Per-context scoping**: Different clients/tenants may need different knowledge packages. Use `before_run()` to scope which collections the agent can search:

```python
# In agent.py
_ACTIVE_COLLECTIONS: ContextVar[tuple[str, ...]] = ContextVar(
    "active_collections", default=("default-collection",)
)

def before_run(input_data: dict) -> dict:
    context = input_data.get("client_context", {})
    packages = context.get("knowledge_packages", [])
    if packages:
        _ACTIVE_COLLECTIONS.set(tuple(packages))
    return input_data
```

### 4. Tools — The Expert's Toolkit

Every domain expert needs these tool categories:

| Category | Examples | Implementation |
|---|---|---|
| **Knowledge search** | Look up rules, standards, definitions | Knowledge MCP (`toolsets=`) |
| **Context lookup** | Client info, history, preferences | Custom tools → external DB/API |
| **Memory** | Notes from previous sessions | Custom tool → persistent store |
| **Web search** | Edge cases not in books | Web search tool as fallback |
| **Communication** | Ask questions, send results | Sandbox tools with `pending_actions` |

### 5. Pause/Resume — The Follow-Up

When the agent needs clarification:
1. Agent returns `status: "needs_clarification"` with a structured question
2. Framework serializes `_message_history` 
3. Host persists the history and shows the question to the human
4. Human answers → host sends answer + stored `message_history` back
5. Agent resumes with full context, incorporates the answer, completes the case

```python
def before_run(input_data: dict) -> dict:
    if input_data.get("message_history"):
        input_data["_instructions"] = (
            "Continue the case. The human has answered your question. "
            "Read their response, incorporate it, and complete your analysis."
        )
    return input_data
```

### 6. Human Approval — Sandbox Tools

Tools that have real-world side effects (sending emails, saving records, making changes) should be **sandbox tools** that return `pending_actions` instead of executing immediately:

```python
@agent.tool_plain
async def send_notification(to: str, subject: str, body: str) -> dict:
    """Send a notification — requires approval before actual delivery."""
    return {
        "pending_action": True,
        "action": "send_notification",
        "params": {"to": to, "subject": subject, "body": body},
        "description": f"Send notification to {to}: {subject}",
    }
```

The host (your product) decides when and how to present these for approval.

## Quick Reference

```bash
# Scaffold the agent
cp -r agents/_template agents/my-expert

# Add knowledge
mkdir -p knowledge/books/my-domain/
# Place PDFs in the directory
# Add collection to knowledge/collections.yaml
# Seed: bash scripts/seed_knowledge.sh (or python -m shared.ingest --all)

# Wire MCP
# In agent.py:
knowledge_server = MCPServerStreamableHTTP(os.environ.get("KNOWLEDGE_MCP_URL"))
agent = create_agent(..., toolsets=[knowledge_server])

# Test knowledge search
docker compose --profile full up -d  # Starts R2R + Knowledge MCP
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| Hardcoding domain rules in Python | Put them in knowledge books. "New rule = new book, not new code." |
| Global knowledge search (no scoping) | Use `before_run()` + ContextVar to scope per client/tenant |
| Skipping the thinking steps in prompt | Add `review_steps: list[str]` to schema — forces the agent to show its work |
| Not handling resume properly | Always check `message_history` in `before_run()` and inject continuation instructions |
| Trusting agent output blindly | Add `confidence: float` and escalate low-confidence results for human review |
| Making all tools execute immediately | Side-effect tools should return `pending_actions` for human approval |
