---
name: brain-clone
description: Use when a domain expert wants to clone their professional brain into an Agent2 agent — interactive multi-phase interview that extracts identity, thinking process, tools, knowledge, examples, and output format, then generates a complete production agent with Chain-of-Thought prompt, Pydantic schemas, tools, knowledge collections, and Docker config. Triggers on "brain clone", "clone expert", "new domain agent", "extract expertise".
---

# Brain Clone

## Overview

Turn a domain expert's brain into a production Agent2 agent through structured interview. The skill extracts tacit professional knowledge — not just facts, but HOW the expert thinks — and generates a complete agent following the proven Sachbearbeiter architecture: 5-layer Chain-of-Thought prompt, tool metaphors, knowledge collections, memory, sandbox tools, and structured output with outcome consistency validation.

**Core insight**: Domain expertise is not a list of rules. It's a thinking process. This skill extracts the process, not the facts. Facts go into knowledge books. Thinking goes into the prompt.

## When to Use

- Domain expert wants to "clone" their professional decision-making into an AI agent
- User says "brain clone", "clone my brain", "create domain expert", "extract my expertise"
- Building an agent for a regulated/specialized domain (accounting, legal, medical, compliance, procurement, HR, insurance)
- Need to go beyond simple "You are an expert in X" prompts to Sachbearbeiter-level Chain-of-Thought

**Do NOT use for**: Generic chatbots, simple CRUD agents, or agents that don't need domain expertise. Use `creating-agents` skill instead.

## The 5-Layer Prompt Architecture

Every brain-clone agent produces a prompt with these layers (derived from the Sachbearbeiter pattern):

```
Layer 1: IDENTITY + MINDSET
  "You are a senior [role] with [N] years of experience..."
  → WHO the agent is, HOW they approach work

Layer 2: WORKSPACE (Tool Metaphors)
  "You sit at your desk and have everything you need:"
  - Reference books → search(), get_passage()
  - Internet → web_search()
  - Client file → get_{context}_info()
  - Database/registry → lookup_{entity}(), list_{entities}()
  - Notepad → update_{context}_memory()
  → Every tool gets a HUMAN metaphor the LLM understands

Layer 3: CHAIN OF THOUGHT (Thinking Process)
  "When you process a [case], you work through it step by step:"
  - "What do I have here?" (intake/classification)
  - "What do I know about this context?" (context lookup)
  - "Is this formally correct?" (validation)
  - "Is anything unclear?" (clarification check)
  - "How do I process this?" (core domain logic)
  - "What did I learn?" (memory update)
  → Steps extracted from the expert's actual thinking process

Layer 4: EXAMPLE THOUGHT PROCESSES
  3-5 real cases showing different outcomes and edge cases
  → NOT rules, but demonstrations of HOW TO THINK

Layer 5: THREE OUTCOMES (Decision Tree)
  Every case ends with exactly one of three results:
  - complete — work product delivered
  - needs_clarification — expert needs human input
  - rejected — input is defective/unusable
  → Clear, mutually exclusive outcomes
```

## The Interview: 8 Phases

Run each phase as a conversation. Do NOT skip phases. Do NOT generate code until Phase 7.

### Phase 1: Identity

**Goal**: Understand WHO this expert is and their professional mindset.

Ask:
- "What's your professional role? What do you do day-to-day?"
- "How long have you been doing this?"
- "What separates you from a beginner in your field?"
- "How would you describe your work style — thorough, efficient, cautious?"

**Extract**: Role title, years of experience, core competency description, personality traits that affect work quality (e.g., "thorough when needed, efficient when possible — never guesses").

**Map to Layer 1**: The identity paragraph of the system prompt.

### Phase 2: Thinking Process

**Goal**: Extract the expert's ACTUAL step-by-step reasoning when they handle a case.

Ask:
- "When a new [case/document/request] lands on your desk, what are your FIRST 3 thoughts?"
- "Walk me through a specific recent case from start to finish — every step, every decision."
- "At which points do you feel certain? At which points do you hesitate?"
- "When do you decide to look something up vs. trust your knowledge?"
- "When do you ask someone else for input? What triggers that?"
- "When do you reject something outright? What makes something unworkable?"

**Extract**: Ordered list of thinking steps with decision points. This becomes Layer 3.

**Critical**: Do NOT accept vague answers like "I analyze it". Push for specifics: "What exactly do you check first? Then what?"

### Phase 3: Tools and Workspace

**Goal**: Map the expert's real-world tools to Agent2 tool categories.

Ask:
- "What's on your desk right now? What do you reach for?"
- "Which reference books/manuals/regulations do you consult?"
- "What databases or systems do you use?"
- "Do you keep personal notes about clients/cases? What's in them?"
- "When do you use the internet to look something up?"
- "Do you ever need to send messages/emails as part of your work?"
- "Do you look up history of past similar cases?"

**Extract and map**:

| Expert says | Tool category | Implementation |
|---|---|---|
| "I check the regulation book" | Knowledge search | Knowledge MCP: search(), get_passage() |
| "I look up the client file" | Context lookup | get_{context}_info() → external DB |
| "I check my notes from last time" | Memory | get_{context}_info() (memory field) |
| "I update my notes" | Memory write | update_{context}_memory() |
| "I look up the supplier/vendor/entity" | Entity lookup | lookup_{entity}(), list_{entities}() |
| "I check past cases" | History | get_{domain}_history() |
| "I Google it when books don't help" | Web search | web_search() (Tavily/DuckDuckGo) |
| "I send an email to ask" | Communication | send_{action}_email() — SANDBOX tool |
| "I save a new record" | Data mutation | save_{entity}() — SANDBOX tool |
| "I scan/read the document" | OCR/intake | Docling MCP: convert + export |

**Workspace metaphor**: For each tool, create a human-readable metaphor: "Your bookshelf with regulations" for knowledge, "Your notepad" for memory, "Your filing cabinet" for entity lookups.

### Phase 4: Knowledge and Reference Material

**Goal**: Identify what goes into R2R knowledge collections.

Ask:
- "Which books, manuals, or regulations are ESSENTIAL for your work?"
- "If you could only keep 3 reference books on your desk, which ones?"
- "Do you have PDFs, tables, or documents you consult regularly?"
- "Are there different reference sets for different clients/contexts?"
- "How do you use these books — cover to cover or specific lookups?"
- "Can you share these files with me?" (collect file paths)

**Extract**:
- List of knowledge collections with descriptions
- Whether collections are universal or per-tenant scoped
- File paths for ingestion

**Generate**:
```yaml
# knowledge/collections.yaml entry
collections:
  {domain}-standards:
    description: "Core regulations and standards for {domain}"
    books_dir: books/{domain}-standards/
    agents:
      - {agent-name}
  {domain}-reference:
    description: "Textbooks, commentaries, practical guides"
    books_dir: books/{domain}-reference/
    agents:
      - {agent-name}
```

### Phase 5: Example Cases

**Goal**: Collect 3-5 diverse cases that demonstrate different thinking paths and outcomes.

Ask:
- "Give me a TYPICAL case and walk me through your reasoning."
- "Give me a case where you had to ask for clarification — what was unclear?"
- "Give me a case where you rejected the input — what was wrong with it?"
- "What's the most COMPLEX case you've handled recently?"
- "What are the most common MISTAKES beginners make?"

**Extract**: For each case, capture:
1. What the input looked like
2. What the expert thought at each step
3. What the outcome was and why
4. What made this case different from others

**Map to Layer 4**: Write each as a brief thought-process narrative (not a rule, but a demonstration of thinking). Keep them short — 2-3 sentences each, like the Sachbearbeiter examples.

### Phase 6: Output Format

**Goal**: Design the Pydantic schema for the agent's structured output.

Ask:
- "When you finish a case, what does your work product look like?"
- "What fields/data points must ALWAYS be present?"
- "What fields are only present in certain outcomes?"
- "How do you express confidence — when are you 90% sure vs. 60%?"
- "What does a 'needs clarification' result look like?"
- "What does a 'rejected' result look like?"

**Extract**: Field list with types, required/optional status, and validation rules.

**Generate schema following the Sachbearbeiter pattern**:

```python
class {Name}Result(BaseModel):
    status: Literal["complete", "needs_clarification", "rejected"]

    # Domain-specific output fields (only when complete)
    {domain_fields}: ...

    # Clarification path
    proposed_message: ClarificationRequest | None = None

    # Rejection path
    rejection_reason: str | None = None

    # Always present
    extracted_fields: Extracted{Domain}Fields
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str  # The expert's chain of thought for THIS case
    review_steps: list[str] = Field(default_factory=list)
    pending_actions: list[PendingAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_status_consistency(self) -> Self:
        """Enforce mutual exclusivity of outcomes."""
        # complete → domain output required, no rejection_reason
        # needs_clarification → proposed_message required
        # rejected → rejection_reason required, no domain output
```

### Phase 7: Generation

**Goal**: Generate all Agent2 artefacts from the collected interview data.

Generate these files in `agents/{name}/`:

**1. `schemas.py`** — Pydantic models from Phase 6
- Include `PendingAction`, `ClarificationRequest`, extracted fields model
- Add `@model_validator` enforcing outcome consistency

**2. `agent.py`** — Full agent module:
- System prompt assembled from Layers 1-5 (Phases 1-5)
- `create_agent()` with `instructions=""` (prompt injected via before_run)
- Tool registrations from Phase 3 mapping
- `before_run()`: collection scoping, context injection into prompt, resume handling
- `after_run()`: persistence, low-confidence escalation
- `mock_result()`: schema-compliant mock for each outcome

**3. `tools.py`** — Tool implementations:
- Knowledge: via MCP toolsets (not in tools.py)
- Context/Memory/History/Lookup: async functions calling external DB
- Web search: Tavily with DuckDuckGo fallback
- Sandbox tools: return `{"pending": True, "action": "...", "params": {...}}`

**4. `config.yaml`**:
```yaml
name: {agent-name}
description: "{one-line from Phase 1}"
model: ""  # Uses DEFAULT_MODEL
port: {next-available}
timeout_seconds: 300
max_retries: 3
collections:
  - {from Phase 4}
capabilities:
  - resume
  - approval_workflow
  - knowledge_mcp
```

**5. `main.py`**: `from shared.api import create_app; app = create_app("{name}")`

**6. `Dockerfile`**: Based on template, with agent-specific dependencies

**7. `docker-compose.yml` entry**: New service block with correct port and environment

**8. `knowledge/collections.yaml` update**: Add new collections from Phase 4

### Phase 8: Review and Iteration

**Goal**: Validate the generated agent with the domain expert.

Present the generated system prompt to the expert and ask:
- "Read this carefully. Does this sound like how YOU think?"
- "Is any step missing from the thinking process?"
- "Are the example cases accurate?"
- "Would you trust this agent to handle a real case?"
- "What would a beginner get wrong that I should add as a warning?"

Iterate until the expert says: **"Yes, that's me."**

After approval:
- Run `uv run pytest tests/ -v` to verify framework integrity
- Build Docker image: `docker compose build {name}`
- Test mock mode: `POST /tasks?mode=sync` with sample input
- If knowledge files were provided: add ingestion instructions

## System Prompt Template

Use this template when assembling the prompt in Phase 7. Replace placeholders with interview data:

```python
SYSTEM_PROMPT = """\
{layer_1_identity}

## Your Workspace

You sit at your desk and have everything you need:

{layer_2_workspace_tools}

Use these tools naturally — reach for them when you need them, not mechanically.

## How You Think

When you process a {case_type}, you work through it step by step. Document your \
process in review_steps[] and explain your decisions in reasoning.

{layer_3_chain_of_thought_steps}

## Example Thought Processes

These are typical cases. Your reality is much broader — use these as orientation, \
not as templates.

{layer_4_examples}

## {context_variable_section}

{dynamic_context_injection_placeholder}

## Three Outcomes

Every {case_type} ends with one of three results:

- **complete** — {complete_description}
- **needs_clarification** — {clarification_description}
- **rejected** — {rejection_description}

## Sandbox Tools

{sandbox_tools_description}

## Pause/Resume

If message_history is present: the case continues. Read the context, use the \
human's answer, complete the work — no re-processing needed.

## Output Format

{format_constraints}
"""
```

## Tool Generation Patterns

### Sandbox Tools (Side Effects)

Any tool that DOES something in the real world must be a sandbox tool:

```python
async def save_{entity}(...) -> dict:
    """SANDBOX: Returns pending action for human approval."""
    return {
        "pending": True,
        "action": "save_{entity}",
        "params": {params},
        "description": f"Save new {entity} '{name}'",
    }

async def _execute_save_{entity}(...) -> dict:
    """REAL execution — called after human approval."""
    # Actual DB/API call here
```

### Memory Tools

Every domain expert agent needs persistent memory:

```python
async def get_{context}_info(context_id: str) -> dict:
    """Load context details and the expert's notes from previous sessions."""

async def update_{context}_memory(context_id: str, memory: str) -> dict:
    """Update persistent memory with learnings from this session.
    Read existing memory first, merge, then save. Max 10,000 chars."""
```

### Knowledge Scoping

Per-tenant or per-context knowledge collections:

```python
_ACTIVE_COLLECTIONS: ContextVar[tuple[str, ...]] = ContextVar(
    "active_collections", default=DEFAULT_COLLECTIONS
)

def before_run(input_data: dict) -> dict:
    context = input_data.get("{context_key}", {})
    collections = context.get("knowledge_collections", [])
    if collections:
        _ACTIVE_COLLECTIONS.set(tuple(collections))
    # Inject dynamic prompt sections
    input_data["_instructions"] = SYSTEM_PROMPT.format(...)
    return input_data
```

## before_run Pattern

Every brain-clone agent uses `before_run()` for:

1. **Knowledge collection scoping** — set active collections from input context
2. **Dynamic prompt injection** — inject context-specific sections into the system prompt (like SKR warning in Sachbearbeiter)
3. **Langfuse prompt fallback** — try Langfuse prompt management first (editable without redeploy), fall back to local SYSTEM_PROMPT
4. **Resume detection** — check for `message_history` and adjust instructions
5. **Input guards** — validate prerequisites (like OCR availability)
6. **Per-run MCP toolsets** — create fresh `MCPServerStreamableHTTP` instances per run to avoid cancel scope collisions when multiple async tasks run concurrently

```python
def before_run(input_data: dict) -> dict:
    # 1. Scope knowledge collections
    context = input_data.get("{context_key}", {})
    collections = context.get("knowledge_collections", [])
    if collections:
        _ACTIVE_COLLECTIONS.set(tuple(collections))

    # 2. Build dynamic prompt sections from context
    dynamic_section = _build_dynamic_section(context)

    # 3. Try Langfuse prompt first, fall back to local
    from shared.config import Settings
    from shared.runtime import get_prompt
    langfuse_prompt = get_prompt(
        "{agent-name}-system-prompt", Settings.from_env(),
        dynamic_section=dynamic_section,
    )
    input_data["_instructions"] = langfuse_prompt or SYSTEM_PROMPT.format(
        dynamic_section=dynamic_section,
    )

    # 4. Resume detection
    if input_data.get("message_history"):
        pass  # _instructions already set; framework handles history

    # 5. Input guards
    if not docling_mcp_url and input_data.get("requires_ocr"):
        raise ValueError("OCR tool not available")

    # 6. Fresh MCP toolsets per run
    input_data["_toolsets"] = _create_mcp_toolsets()
    return input_data
```

## after_run Pattern

Every brain-clone agent uses `after_run()` for:

1. **Persist results** to external DB/API
2. **Low-confidence escalation** — flag results below threshold for human review
3. **Message threading** — append to existing conversation threads
4. **Error recovery** — set error status if persistence fails

```python
async def after_run(input_data: dict, output: dict) -> None:
    job_id = input_data.get("{job_id_field}")
    if not job_id:
        return
    # Persist
    # Escalate if confidence < 0.85
    if output.get("confidence", 0) < 0.85:
        output["needs_review"] = True
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| Skipping Phase 2 (thinking process) | This IS the skill. Without it you get "You are an expert" — worthless. Push for step-by-step specifics. |
| Encoding domain knowledge in the prompt | Knowledge goes in R2R collections. The prompt teaches HOW TO THINK, not WHAT TO KNOW. |
| Generic tool names | Use domain language: "lookup_lieferant" not "search_entity". The LLM performs better with domain-specific naming. |
| Skipping the review loop (Phase 8) | The expert MUST validate. "Does this sound like how you think?" is the only real test. |
| Making all tools execute immediately | Side-effect tools MUST be sandboxed with pending_actions. Always. |
| Single knowledge collection | Split by purpose: standards vs. reference material vs. per-tenant packages. |
| No model_validator on schema | Without it, the LLM can return contradictory state (e.g., complete + rejection_reason). PydanticAI retries on validation errors. |
| Hardcoding prompt without before_run | Dynamic sections (like context-specific rules) must be injected per-run via `_instructions`. |
| Forgetting mock_result | Without it, the API is untestable in dev mode. Generate schema-compliant mocks for each outcome. |

## Cross-References

- **REQUIRED**: `creating-agents` skill for file scaffolding and Docker wiring
- **REQUIRED**: `building-domain-experts` skill for the domain expert pattern reference
- **REQUIRED**: `adding-knowledge` skill for R2R collection setup and ingestion
- **OPTIONAL**: `adding-capabilities` skill for pause/resume and approval workflow details
