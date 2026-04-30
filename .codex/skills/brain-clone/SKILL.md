---
name: brain-clone
description: Use when a domain expert wants to clone their professional brain into an Agent2 agent — interactive multi-phase interview that extracts identity, Chain-of-Thought, tools, knowledge, examples, and output format, then generates a complete production agent with a Sachbearbeiter-style Chain-of-Thought prompt, Pydantic schemas, tools, knowledge collections, and Docker config. Triggers on "brain clone", "clone expert", "new domain agent", "extract expertise".
---

# Brain Clone

## Overview

Turn a domain expert's brain into a production Agent2 agent through structured interview. The skill extracts tacit professional knowledge — not just facts, but the expert's Chain-of-Thought — and generates a complete agent following the proven Sachbearbeiter architecture: 5-layer Chain-of-Thought prompt, tool metaphors, knowledge collections, memory, sandbox tools, and structured output with outcome consistency validation.

Canonical references in this repo:
- `docs/brain-clone-pattern.md` explains the Agent2 Brain Clone pattern.
- `docs/reference-agents/sachbearbeiter-pattern.md` explains the production reference architecture.
- `agents/procurement-compliance-officer` is the full public flagship example to study before generating a serious domain agent.

**Core insight**: Domain expertise is not a list of rules. It is a Sachbearbeiter-style Chain-of-Thought: a professional mental loop of intake, lookup, checking, clarification, decision, and memory update. Facts go into knowledge books. The expert's Chain-of-Thought goes into the prompt.

**Important**: In Agent2, "Chain-of-Thought" means the domain professional's explicit work-thinking pattern, not a request to expose private model internals. The prompt should make the agent run the expert's mental chain; the output should expose concise `reasoning` and `review_steps[]` as the observable trace of that work.

## When to Use

- Domain expert wants to "clone" their professional decision-making into an AI agent
- User says "brain clone", "clone my brain", "create domain expert", "extract my expertise"
- Building an agent for a regulated/specialized domain (accounting, legal, medical, compliance, procurement, HR, insurance)
- Need to go beyond simple "You are an expert in X" prompts to Sachbearbeiter-level Chain-of-Thought prompts

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

Layer 3: SACHBEARBEITER CHAIN OF THOUGHT
  "When you process a [case], you work through it step by step:"
  - "What do I have here?" (intake/classification)
  - "What do I know about this context?" (context lookup)
  - "Is this formally correct?" (validation)
  - "Is anything unclear?" (clarification check)
  - "How do I process this?" (core domain logic)
  - "What did I learn?" (memory update)
  → The professional reasoning chain extracted from the expert's actual work

Layer 4: EXAMPLE CHAINS OF THOUGHT
  3-5 real cases showing different outcomes and edge cases
  → NOT rules, but demonstrations of the expert's thinking chain

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

**Goal**: Extract the expert's ACTUAL Chain-of-Thought when they handle a case.

Ask:
- "When a new [case/document/request] lands on your desk, what are your FIRST 3 thoughts?"
- "Walk me through a specific recent case from start to finish — every step, every decision."
- "At which points do you feel certain? At which points do you hesitate?"
- "When do you decide to look something up vs. trust your knowledge?"
- "When do you ask someone else for input? What triggers that?"
- "When do you reject something outright? What makes something unworkable?"

**Extract**: Ordered Chain-of-Thought with decision points. This becomes Layer 3.

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

**Map to Layer 4**: Write each as a brief Chain-of-Thought narrative (not a rule, but a demonstration of thinking). Keep them short — 2-3 sentences each, like the Sachbearbeiter examples.

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
    reasoning: str  # Concise observable Chain-of-Thought summary for THIS case
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
- Tests and Promptfoo evals that prove behavior, not just JSON shape

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
- "Is any step missing from the Chain-of-Thought?"
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

## Sachbearbeiter Chain of Thought

When you process a {case_type}, run the expert Chain-of-Thought step by step. \
Document the visible checkpoints in review_steps[] and summarize the decision \
chain in reasoning.

{layer_3_chain_of_thought_steps}

## Example Chains of Thought

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

### Chain-of-Thought Checkpoint Tool

For complex expert agents, add a no-op checkpoint tool that makes the model walk
the Sachbearbeiter Chain-of-Thought before deciding. This tool does not persist
anything and does not expose private model internals; it records the visible case
checkpoint the professional would write on their scratchpad.

```python
@agent.tool_plain
async def note_review_step(step: str, finding: str, next_action: str = "") -> dict:
    """Record a visible checkpoint in the expert Chain-of-Thought."""
    return {
        "recorded": True,
        "step": step,
        "finding": finding,
        "next_action": next_action,
    }
```

Use this when the real expert would pause and think: classify the case, choose a
book to open, decide whether facts are missing, or decide between completion,
clarification, and rejection.

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
6. **Per-run MCP toolsets** — create fresh `MCPServerStreamableHTTP` instances per run to avoid cancel scope collisions when multiple async tasks run concurrently. Agent2 passes `_toolsets` into `Agent.run(toolsets=...)`.

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
| Skipping Phase 2 (Chain-of-Thought) | This IS the skill. Without it you get "You are an expert" — worthless. Push for step-by-step specifics. |
| Encoding domain knowledge in the prompt | Knowledge goes in R2R collections. The prompt teaches HOW TO THINK, not WHAT TO KNOW. |
| Generic tool names | Use domain language: "lookup_lieferant" not "search_entity". The LLM performs better with domain-specific naming. |
| Skipping the review loop (Phase 8) | The expert MUST validate. "Does this sound like how you think?" is the only real test. |
| Making all tools execute immediately | Side-effect tools MUST be sandboxed with pending_actions. Always. |
| Single knowledge collection | Split by purpose: standards vs. reference material vs. per-tenant packages. |
| No model_validator on schema | Without it, the LLM can return contradictory state (e.g., complete + rejection_reason). PydanticAI retries on validation errors. |
| Hardcoding prompt without before_run | Dynamic sections (like context-specific rules) must be injected per-run via `_instructions`. |
| Forgetting mock_result | Without it, the API is untestable in dev mode. Generate schema-compliant mocks for each outcome. |
| Ignoring the flagship example | Study `agents/procurement-compliance-officer` before generating a full domain expert. |

## Anti-Sycophancy Rules

The interviewer must behave like a rigorous YC partner, not a polite note-taker.
The first answer to any question is usually the polished version. The real answer
comes after the second or third push.

**Never say these during the interview (Phases 1-6):**
- "That's an interesting approach" — take a position instead
- "I see, that makes sense" — probe whether it actually makes sense in production
- "There are many ways to think about this" — pick one and state what evidence
  would change your mind
- "You might want to consider..." — say "This is wrong because..." or "This
  works because..."
- "Got it" — restate what you understood and ask if that matches reality

**Always do:**
- Take a position on every answer. State your position AND what evidence would
  change it.
- Push once, then push again. The first answer is aspirational. The second is real.
- Challenge the strongest version of the expert's claim, not a strawman.
- Name common failure patterns: "sounds like you're describing how you WISH you
  worked, not how you ACTUALLY work — is that fair?"

## Forcing Questions & Pushback Patterns

Every phase has forcing-quality questions. Do NOT accept abstract or generic
answers. Push until you hear specifics: a field name, a regulation section, a
concrete threshold, a real case.

### Phase 1 Pushback Patterns

| Expert says | BAD follow-up (avoid) | FORCING follow-up (aim for) |
|---|---|---|
| "I'm thorough and careful" | "Great, tell me more about your style" | "Give me an example where being thorough cost you 30 minutes but saved the client money. What did a beginner miss that you caught?" |
| "I have 20 years of experience" | "That's impressive, what's your specialty?" | "What do you know today that you got wrong in year 5? What's the most expensive mistake you stopped making?" |
| "I handle invoices" | "What kind of invoices?" | "Pick the last invoice that made you pause. Not routine — the tricky one. What was on it?" |

### Phase 2 Pushback Patterns (THE critical phase)

| Expert says | BAD follow-up (avoid) | FORCING follow-up (aim for) |
|---|---|---|
| "First I analyze the document" | "What do you analyze?" | "'Analyze' is too vague for a production agent. When the PDF opens, where do your eyes go FIRST — top-right for the amount? Bottom for the tax line? What tells you in the first 3 seconds whether this is routine or trouble?" |
| "I check if everything is correct" | "What counts as correct?" | "Name the last invoice you rejected. What SPECIFIC field was wrong? Was it missing entirely, or present but wrong? How did you know it was wrong — from memory, from a regulation, or from the client file?" |
| "I look things up when needed" | "What do you look up?" | "Last week — what did you look up and what did you already know? What's the threshold where you stop trusting your memory and open the book?" |
| "It depends on the situation" | "Can you give me examples?" | "'It depends' means there's a decision tree in your head. Let's map it. What are the 2-3 things it depends ON? For each one, what do you do differently?" |
| "I use my experience" | "How does experience help?" | "Experience means you have mental shortcuts a beginner doesn't. Name one. What does a beginner check that you skip because you already know the answer? What does a beginner miss that you catch without thinking?" |

### Phase 3 Pushback Patterns

| Expert says | BAD follow-up (avoid) | FORCING follow-up (aim for) |
|---|---|---|
| "I use various databases" | "Which ones?" | "Open your browser right now. What tabs are open? What bookmarks do you use weekly? Name the 3 systems you'd be paralyzed without." |
| "I check regulations" | "Which regulations?" | "You have a client's invoice for EUR 2,380 consulting. Which EXACT section do you open? Do you search by keyword or flip to a known page? What's the search term?" |

### Phase 5 Pushback Patterns

| Expert says | BAD follow-up (avoid) | FORCING follow-up (aim for) |
|---|---|---|
| "I usually approve these" | "What makes you approve?" | "Walk me through the LAST one you approved. What was the amount? Who was the vendor? What made it a clear approve versus needing a second look?" |
| "Sometimes I need to ask" | "What do you ask about?" | "Show me the last email or message you sent to a client asking for clarification. What EXACTLY was unclear? What would have happened if you'd guessed instead of asking?" |
| "I reject bad invoices" | "What makes them bad?" | "Name the last rejection. What was wrong? Was it fixable (send corrected invoice) or unfixable (fraudulent)? How did you communicate the rejection?" |

## Phase 2.5: Premise Challenge (NEW — insert between Phase 2 and Phase 3)

**Goal**: Validate that the extracted Chain-of-Thought matches reality, not
aspiration. Experts describe how they WISH they worked, not how they ACTUALLY
work. This phase catches the gap.

Before moving to Phase 3 (Tools), synthesize the thinking chain from Phase 2
and present it as explicit premises:

```
Based on what you described, here are the premises I'm building the agent on.
If any of these are wrong, the agent will be wrong in production.

PREMISES:
1. [You always check X before Y] — true in every case, or only when Z?
2. [You reach for the book when the amount exceeds threshold T] — is T a hard
   number or a gut feeling?
3. [You never reject without attempting clarification first] — even when the
   document is clearly fraudulent?
4. [Your first step is always intake/classification] — or do you sometimes
   skip straight to booking for known recurring vendors?
5. [You update your notes at the end of every session] — really every time,
   or only when something surprising happened?
```

**Rules:**
- Extract 4-6 premises from the Phase 2 answers.
- Each premise must be specific enough that the expert can say "yes exactly" or
  "no, actually..."
- Frame premises as potentially wrong — make it easy to correct them.
- If the expert corrects a premise, UPDATE the Chain-of-Thought from Phase 2.
- Do NOT proceed to Phase 3 until all premises are confirmed or corrected.

**Pushback pattern:**
- Expert says "Yes, that's right" to everything → "I'm suspicious. Nobody's
  process is this clean. Tell me about the last time you DIDN'T follow this
  process. What made you skip a step?"

## Phase 6.5: Scope Decision (NEW — insert between Phase 6 and Phase 7)

**Goal**: Make deliberate architectural decisions before generating code.

Present via structured questions:

**Scope Question 1: Agent Boundary**
> "Is this one agent or should some responsibilities be separate? For example:
> should OCR intake be a preprocessing step before the agent runs? Should
> knowledge search be shared infrastructure used by multiple agents?"

Options:
- A) Single agent handles everything (simpler, recommended for first version)
- B) Split: [describe the split based on interview data]

**Scope Question 2: Knowledge Sharing**
> "Should the knowledge collections be exclusive to this agent or shared with
> others in your organization?"

Options:
- A) Exclusive — this agent owns its books
- B) Shared — other agents may search the same collections

**Scope Question 3: Execution Model**
> "When this agent decides to take action (send email, save record), should it:"

Options:
- A) Propose and wait for human approval (sandbox mode — recommended for
  regulated domains)
- B) Execute directly (autonomous mode — for low-risk domains)

**Scope Question 4: Minimal Viable Agent**
> "What's the smallest version of this agent that would be useful in production
> THIS WEEK? Not the full vision — the wedge."

Push for a concrete answer. The wedge becomes the Phase 7 generation target.
The full vision goes into config.yaml as future capabilities.

## Phase 7.5: Architecture Review by Fresh Eyes (NEW — insert between Phase 7 and Phase 8)

**Goal**: Independent validation of the generated agent before the expert reviews.

After Phase 7 generates all files, dispatch a review of the generated code.
The reviewer sees ONLY the generated files, NOT the interview context. This
ensures genuine independence.

**Review dimensions:**

1. **Completeness** — Does every tool referenced in the prompt exist in tools.py?
   Does every outcome in the prompt have a matching schema path? Does
   mock_result() cover all three outcomes?

2. **Consistency** — Do the schema field names match what the prompt tells the
   agent to produce? Does the model_validator catch all contradictory states?
   Do the tool function signatures match what the prompt describes?

3. **Clarity** — Could a developer with zero interview context read agent.py and
   understand what this agent does? Are the tool docstrings in domain language?

4. **Domain Fit** — Do tool names sound like domain vocabulary ("lookup_lieferant")
   or generic abstractions ("search_entity")? Does the prompt read like a
   professional talking or like a requirements document?

5. **Production Readiness** — Does before_run() scope knowledge collections?
   Does after_run() handle persistence failures? Is there a mock_result()?
   Are MCP toolsets created per-run?

**Output**: A numbered list of issues with severity (CRITICAL / IMPORTANT / NICE).
Fix CRITICAL issues before proceeding to Phase 8. Present IMPORTANT issues to
the expert during Phase 8. Log NICE issues as TODOs in the generated code.

## Agent Quality Rating (run after Phase 8)

After the expert approves, rate the generated agent on these dimensions.
This makes quality visible and specific.

| Dimension | Score | What a 10 looks like for THIS agent |
|---|---|---|
| Chain-of-Thought Depth | ?/10 | The thinking chain is specific enough that a junior in the domain could use it as a processing checklist |
| Tool Coverage | ?/10 | Every physical tool on the expert's desk has a corresponding agent tool with domain-language naming |
| Knowledge Completeness | ?/10 | All books, regulations, and reference materials are specified as collections with real source documents |
| Example Diversity | ?/10 | Examples cover complete, clarification, rejection, AND at least one complex edge case with split logic |
| Schema Strictness | ?/10 | model_validator prevents every contradictory state; no valid JSON can represent an impossible outcome |
| Workspace Metaphor Quality | ?/10 | Reading the prompt feels like sitting at the expert's desk, not reading a requirements spec |
| Production Readiness | ?/10 | before_run, after_run, mock_result, per-run toolsets, knowledge scoping, resume detection all present |
| Eval Coverage | ?/10 | Promptfoo evals test real domain behavior (correct outcome, correct reasoning) not just JSON shape |

**Scoring rules:**
- Below 6 on any dimension → the agent is not ready for production. Fix before deploying.
- Below 8 on Chain-of-Thought Depth → the interview was too shallow. Go back to Phase 2.
- Below 7 on Example Diversity → go back to Phase 5 and collect more cases.
- Report the total score (out of 80) and the weakest dimension.

## Agent Slop Detection

After generation, scan for these anti-patterns that indicate a generic agent
rather than a genuine brain clone. Each detected pattern is a generation failure
that must be fixed before Phase 8 review.

| Pattern | What it looks like | Fix |
|---|---|---|
| Identity slop | "You are an expert in X" or "You are a helpful X assistant" | Rewrite with specific years, style traits, and what separates this expert from a beginner |
| Tool name slop | `search_entity()`, `process_input()`, `get_data()` | Rename to domain language: `lookup_lieferant()`, `get_mandant_info()`, `search_kontenrahmen()` |
| Missing workspace | Tools listed without desk metaphor | Add "You sit at your desk and have:" with human-readable metaphors for each tool |
| Uniform examples | All examples end with "complete" or all follow the same structure | Ensure examples cover different outcomes, different complexity levels, and at least one surprise |
| Abstract Chain-of-Thought | "Analyze the input" / "Check for correctness" / "Process the request" | Replace with specific checks: "What field is missing?" / "Is the tax ID in the right format?" / "Does the amount match the line items?" |
| Missing clarification triggers | No guidance on WHEN to ask vs. decide | Add explicit triggers: "Ask when X is ambiguous. Decide when Y is clear. Never guess about Z." |
| Hardcoded domain knowledge | Lookup tables, account mappings, or rules embedded in the prompt | Move to knowledge collections. The prompt teaches HOW to think, books contain WHAT to know. |
| Missing memory structure | No guidance on what to remember between sessions | Add memory template with sections relevant to the domain |
| Single-outcome mock | mock_result() only returns "complete" | Generate mocks for all three outcomes with realistic field values |
| No resume handling | Missing message_history detection in before_run | Add resume detection: if message_history present, continue case without re-processing |

**Rule:** If 3+ slop patterns are detected, the generation failed. Go back to
the interview phase that produced the weak output (usually Phase 2 or Phase 5).

## Interview Session Persistence

Brain Clone interviews can span multiple sessions. Persist interview state so
the conversation can resume.

After each completed phase, write state to disk:

```bash
mkdir -p ~/.agent2/brain-clone-sessions
```

```json
{
  "agent_name": "my-agent",
  "started_at": "2026-04-30T10:00:00Z",
  "current_phase": 3,
  "completed_phases": {
    "phase_1": {"identity": "...", "completed_at": "..."},
    "phase_2": {"chain_of_thought": "...", "completed_at": "..."},
    "phase_2_5": {"premises": [...], "corrections": [...], "completed_at": "..."}
  },
  "pending_phase": 3,
  "expert_name": "...",
  "domain": "..."
}
```

On skill start, check for existing sessions:

```bash
ls ~/.agent2/brain-clone-sessions/*.json 2>/dev/null
```

If a session exists for the current agent name, offer to resume:
> "Found an in-progress brain clone session for '{agent_name}' (Phase {N} of 8,
> started {date}). Resume where you left off?"

Options:
- A) Resume from Phase {N}
- B) Start fresh (overwrites previous session)

## Completion Status Protocol

When completing the Brain Clone workflow, report status using one of:

- **DONE** — Agent generated, reviewed, and approved by expert. Report the
  Agent Quality Rating score.
- **DONE_WITH_CONCERNS** — Agent generated and approved, but some dimensions
  scored below 7. List the weak dimensions and recommended follow-ups.
- **BLOCKED** — Cannot proceed. State the blocker (e.g., expert unavailable for
  Phase 8 review, knowledge documents not provided, OCR dependency missing).
- **NEEDS_CONTEXT** — Missing information. State exactly what is needed (e.g.,
  "Need 2 more example cases covering rejection outcomes for Phase 5").

Format: `STATUS`, `SCORE` (total /80), `WEAKEST_DIMENSION`, `NEXT_ACTION`.

## Cross-References

- **REQUIRED**: `creating-agents` skill for file scaffolding and Docker wiring
- **REQUIRED**: `building-domain-experts` skill for the domain expert pattern reference
- **REQUIRED**: `adding-knowledge` skill for R2R collection setup and ingestion
- **OPTIONAL**: `adding-capabilities` skill for pause/resume and approval workflow details
