# Brain Clone Pattern

Brain Clone is the recommended way to build serious Agent2 domain agents. It
does not clone facts into code. It extracts how a professional works and gives
the agent the same workspace: books, tools, memory, clarifying questions,
approval paths, and typed output.

## Core Idea

Domain expertise is not a list of rules. It is a Sachbearbeiter-style
Chain-of-Thought: the professional mental chain that moves from intake, to
lookup, to checking, to clarification, to decision, to memory update.

- Facts, policies, tables, regulations, and manuals go into knowledge books.
- The prompt teaches the expert's Chain-of-Thought.
- Tools represent the expert's desk.
- The schema represents the final work product.
- Evals prove the agent behaves like the expert in real cases.

## Five Prompt Layers

### 1. Identity and Mindset

Define who the expert is and what kind of judgment they apply.

Good:

```text
You are a senior procurement compliance officer with 15 years of experience.
You are fast when the case is routine, strict when policy risk appears, and you
never guess.
```

Weak:

```text
You are a helpful procurement AI.
```

### 2. Workspace

Map every tool to a human workplace metaphor:

- policy books -> `search()` and `get_passage()`
- client or department file -> `get_*_context()`
- vendor or entity file -> `lookup_*()`
- case history -> `get_*_history()`
- notepad or memory -> `update_*_memory()`
- outbox -> sandbox communication tool
- approval register -> sandbox write tool

Tool names should use domain language.

### 3. Sachbearbeiter Chain of Thought

Describe the expert's actual thinking chain. In Agent2, Chain-of-Thought means
the domain professional's explicit case-processing loop, not a raw dump of
private model internals. Ask the agent to run this chain and expose operational
artifacts such as `review_steps[]` and a concise `reasoning` field.

Typical flow:

1. What landed on my desk?
2. Which rules apply?
3. What do I know about this context?
4. What is missing?
5. Can I complete the work?
6. Should I reject it?
7. What did I learn for next time?

### 4. Example Chains of Thought

Include a few short cases that demonstrate how to work, not a list of hardcoded
answers. The examples should cover complete, clarification, rejection, and one
complex edge case.

### 5. Three Outcomes

Every serious domain agent should end in exactly one outcome:

- complete or domain-specific equivalent such as `approved`
- `needs_clarification`
- `rejected`

These outcomes must be mutually exclusive in the schema.

## Schema Contract

Use Pydantic models as the operational contract:

```python
class ExpertResult(BaseModel):
    status: Literal["complete", "needs_clarification", "rejected"]
    domain_output: DomainOutput | None = None
    clarification: ClarificationRequest | None = None
    rejection_reason: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    review_steps: list[str] = Field(default_factory=list)
    pending_actions: list[PendingAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_status_consistency(self) -> Self:
        ...
```

The validator is mandatory for full domain agents. It prevents states like
approved plus rejection reason, or clarification without missing fields.

## Runtime Pattern

Use `before_run()` for dynamic runtime setup:

- scope active knowledge collections from request context
- inject dynamic instructions
- detect resume via `message_history`
- validate prerequisites
- create fresh per-run MCP toolsets with `_toolsets`

Agent2's API runtime passes `_toolsets` into `Agent.run(toolsets=...)` and strips
runtime-only keys from the prompt.

Use `after_run()` for host persistence and operational annotations:

- persist result
- flag low-confidence output for human review
- append message thread state
- recover or surface persistence failures

Use `mock_result()` so the API remains useful without an LLM key.

## Knowledge Pattern

Create focused collections:

```yaml
collections:
  procurement-policy-core:
    description: "Procurement policies and approval thresholds"
    books_dir: books/procurement-policy-core/
    agents:
      - procurement-compliance-officer
```

Do not hide domain rules in Python unless the rule is truly runtime mechanics.
If the policy changes, update the book and the eval.

## Canonical In-Repo Example

Study [`agents/procurement-compliance-officer`](../agents/procurement-compliance-officer).
It demonstrates:

- five-layer prompt
- Knowledge MCP
- per-run scoped toolsets
- three outcomes
- `model_validator`
- memory tools
- sandbox pending actions
- resume support
- `after_run`
- schema-valid mock mode
- unit tests and Promptfoo evals

## Production Reference Pattern

See [`docs/reference-agents/sachbearbeiter-pattern.md`](./reference-agents/sachbearbeiter-pattern.md).
It explains the production-proven accounting clerk architecture that inspired
Brain Clone: one professional agent owns one complete case from document intake
through review, communication, and structured output.
