"""Brain Clone onboarding flow for Agent2."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule

from agent2_cli.generator import generate_agent_from_spec
from agent2_cli.spec import (
    AgentIdentity,
    AgentSpec,
    ExampleCaseSpec,
    KnowledgeCollectionSpec,
    OutcomeSpec,
    SchemaFieldSpec,
    ToolSpec,
)
from shared.config import Settings
from shared.runtime import _build_model

BRAIN_CLONE_SYNTHESIS_PROMPT = """\
You are the Agent2 Brain Clone onboarding harness. Convert the user's structured
interview notes into a valid AgentSpec. Preserve the Sachbearbeiter
Chain-of-Thought as explicit operational steps. Do not generate code.
"""

_INTERVIEW_OUTPUT_FORMAT = """
## Output Format When Complete
When you say INTERVIEW_COMPLETE, output a JSON object with these fields:
{
  "name": "kebab-case-agent-name",
  "description": "one-sentence description",
  "identity": {"role": "...", "domain": "...", "years_experience": N, "mindset": "..."},
  "case_type": "what one case looks like",
  "chain_of_thought_steps": ["step 1", "step 2", ...],
  "tools": [{"name": "tool_name", "description": "...", "category": "context|memory|knowledge|web|communication|record", "sandbox": false}],
  "knowledge_collections": [{"name": "collection-slug", "description": "...", "books_dir": "knowledge/books/collection-slug"}],
  "outcomes": [
    {"name": "complete", "description": "..."},
    {"name": "needs_clarification", "description": "..."},
    {"name": "rejected", "description": "..."}
  ],
  "output_fields": [{"name": "domain_output", "type": "dict", "description": "...", "required": false}],
  "example_cases": [{"title": "...", "input_summary": "...", "chain_of_thought": "...", "outcome": "complete"}],
  "port": 8050
}

Start the interview now. Greet the expert warmly and ask about their professional role.
"""

_SKILL_SECTIONS_FOR_INTERVIEW = (
    "## Anti-Sycophancy Rules",
    "## Forcing Questions & Pushback Patterns",
    "### Phase 1:",
    "### Phase 2:",
    "## Phase 2.5:",
    "### Phase 3:",
    "### Phase 4:",
    "### Phase 5:",
    "### Phase 6:",
    "## Phase 6.5:",
)


def _load_interview_prompt_from_skill() -> str:
    """Build the agentic interview prompt from the canonical SKILL.md.

    Extracts the interview phases, anti-sycophancy rules, and forcing questions
    from the brain-clone SKILL.md so there is a single source of truth.
    Falls back to a minimal hardcoded prompt if SKILL.md is unreadable.
    """
    skill_paths = [
        Path(__file__).resolve().parent.parent / ".claude" / "skills" / "brain-clone" / "SKILL.md",
        Path.home() / ".claude" / "skills" / "gstack" / "brain-clone" / "SKILL.md",
    ]
    skill_content = ""
    for p in skill_paths:
        if p.exists():
            try:
                skill_content = p.read_text(encoding="utf-8")
                break
            except OSError:
                continue

    if not skill_content:
        return _FALLBACK_INTERVIEW_PROMPT

    sections: list[str] = []
    lines = skill_content.splitlines()
    capturing = False
    stop_headers = {
        "## The 5-Layer Prompt Architecture",
        "## System Prompt Template",
        "## Tool Generation Patterns",
        "## before_run Pattern",
        "## after_run Pattern",
        "## Common Mistakes",
        "## Cross-References",
        "## Agent Quality Rating",
        "## Agent Slop Detection",
        "## Interview Session Persistence",
        "## Completion Status Protocol",
    }

    for line in lines:
        if any(line.startswith(s) for s in _SKILL_SECTIONS_FOR_INTERVIEW):
            capturing = True
        if capturing and line.startswith("## ") and line.strip() in stop_headers:
            capturing = False
            continue
        if capturing:
            sections.append(line)

    if not sections:
        return _FALLBACK_INTERVIEW_PROMPT

    extracted = "\n".join(sections).strip()

    preamble = """\
You are the Agent2 Brain Clone interviewer. Your job is to interview a domain
expert and extract everything needed to build a production AI agent that clones
their professional brain.

You conduct an adaptive, conversational interview. Each phase has a gate: do NOT
proceed until the current phase yields specific, concrete answers.

"""

    rules = """
## Interview Rules
- Ask ONE question at a time. Wait for the answer before the next question.
- Adapt your questions based on their answers — this is a conversation, not a form.
- Use the expert's domain language, not generic AI terminology.
- When you have enough information for a phase, state the gate result and
  transition naturally.
- Be warm but rigorous. Warmth in tone, rigor in specificity.
- After all phases, summarize and ask if anything is missing.
- When the expert confirms OR says "done", "that's it", "nothing else", or similar,
  immediately finalize. Do NOT ask additional clarifying questions after the user
  signals completion.
- When finalizing, say exactly: "INTERVIEW_COMPLETE" on its own line,
  followed by the collected data as a structured JSON block.
- If the user provides very detailed answers, you can skip ahead — don't pad the
  interview artificially. 8-15 turns total is ideal.
"""

    return preamble + extracted + "\n" + rules + _INTERVIEW_OUTPUT_FORMAT


_FALLBACK_INTERVIEW_PROMPT = """\
You are the Agent2 Brain Clone interviewer. Interview a domain expert across
these phases: (1) Identity, (2) Thinking Process, (2.5) Premise Challenge,
(3) Tools, (4) Knowledge, (5) Example Cases, (6) Output Format, (6.5) Scope.

Ask ONE question at a time. Push for specifics — reject vague answers like
"I analyze it". When done, say INTERVIEW_COMPLETE and output a JSON AgentSpec.
""" + _INTERVIEW_OUTPUT_FORMAT


def _get_interview_prompt() -> str:
    """Return the interview prompt, loading from SKILL.md on first call."""
    if not hasattr(_get_interview_prompt, "_cached"):
        _get_interview_prompt._cached = _load_interview_prompt_from_skill()  # type: ignore[attr-defined]
    return _get_interview_prompt._cached  # type: ignore[attr-defined]


SESSIONS_DIR = Path.home() / ".agent2" / "brain-clone-sessions"


def _save_interview_session(agent_name: str, phase: int, messages: list, console: Console) -> None:
    """Persist interview progress so it can be resumed across sessions."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSIONS_DIR / f"{agent_name}.json"
    session_data = {
        "agent_name": agent_name,
        "current_phase": phase,
        "updated_at": datetime.now().isoformat(),
        "message_count": len(messages),
    }
    try:
        session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")
    except OSError as exc:
        console.print(f"[dim]Could not save session: {exc}[/dim]")


def _check_existing_session(console: Console) -> str | None:
    """Check for in-progress brain clone sessions and offer to resume."""
    if not SESSIONS_DIR.exists():
        return None
    sessions = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not sessions:
        return None
    try:
        data = json.loads(sessions[0].read_text(encoding="utf-8"))
        agent_name = data.get("agent_name", "unknown")
        phase = data.get("current_phase", 0)
        updated = data.get("updated_at", "unknown")[:10]
        console.print(Panel(
            f"[bold]Found in-progress session:[/bold] {agent_name}\n"
            f"Phase {phase}/8, last active {updated}",
            border_style="#252525",
        ))
        resume = Confirm.ask(f"Resume interview for '{agent_name}'?", default=True)
        if resume:
            return agent_name
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _clear_session(agent_name: str) -> None:
    """Remove a completed interview session file."""
    session_file = SESSIONS_DIR / f"{agent_name}.json"
    session_file.unlink(missing_ok=True)


def load_spec(path: Path) -> AgentSpec:
    """Load an AgentSpec from JSON."""

    return AgentSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))


def run_onboarding(
    *,
    project_root: Path,
    from_spec: Path | None = None,
    no_llm: bool = False,
    overwrite: bool = False,
    use_tui: bool = True,
    agentic: bool = False,
    console: Console | None = None,
) -> Path:
    """Run onboarding and generate an Agent2 agent."""

    out = console or Console()
    if from_spec is not None:
        spec = load_spec(from_spec)
    elif agentic and not no_llm and Settings.from_env().has_llm_key:
        spec = asyncio.run(_agentic_interview(out))
    else:
        spec = _tui_questionnaire() if use_tui and textual_available() else _questionnaire(out)
        if not no_llm and Settings.from_env().has_llm_key:
            spec = asyncio.run(_polish_spec_with_llm(spec))

    agent_dir = generate_agent_from_spec(spec, project_root=project_root, overwrite=overwrite)
    out.print()
    out.print(Panel(
        f"[green]✓[/green] Generated [bold]{spec.name}[/bold] at {agent_dir}\n\n"
        f"[bold white]Your agent will run at:[/bold white]\n"
        f"  [#FF3B30]http://localhost:{spec.port}[/]\n\n"
        f"[bold white]Useful commands:[/bold white]\n"
        f"  uv run agent2 serve {spec.name}   [#777]# start the agent API[/]\n"
        f"  uv run agent2 run {spec.name}     [#777]# send a test request[/]\n"
        f"  uv run agent2 doctor              [#777]# check your setup[/]\n\n"
        f"[bold white]Next steps:[/bold white]\n"
        f"  [#9A9590]• Add knowledge books to knowledge/books/[/]\n"
        f"  [#9A9590]• Open in Claude Code and run /brain-clone to refine[/]\n"
        f"  [#9A9590]• Deploy with Docker: docker compose up {spec.name}[/]",
        title="[bold #FF3B30]●[/bold #FF3B30] [bold]Agent Ready[/bold]",
        border_style="#252525",
        padding=(1, 2),
    ))
    return agent_dir


def _questionnaire(console: Console) -> AgentSpec:
    console.print("[bold]Agent2 Brain Clone[/bold]")
    console.print("Answer a few questions. Agent2 will generate a sandbox-first domain agent.")

    name = Prompt.ask("Agent name (kebab-case)", default="my-brain-clone")
    role = Prompt.ask("Professional role", default="Roofing estimator")
    domain = Prompt.ask("Domain", default="roofing and building repair")
    years = IntPrompt.ask("Years of experience", default=10)
    case_type = Prompt.ask("What does one case/request look like?", default="customer repair request")
    description = Prompt.ask("One-sentence agent description", default=f"Processes {case_type} like an expert {role}.")
    mindset = Prompt.ask("Expert mindset", default="Practical, safety-aware, detail-oriented, and never guesses.")

    steps: list[str] = []
    console.print("\n[bold]Sachbearbeiter Chain-of-Thought steps[/bold]")
    for index, default in enumerate(
        [
            "What landed on my desk?",
            "What context or history do I need?",
            "Which rules, constraints, or safety issues apply?",
            "What is missing or unclear?",
            "Can I complete, clarify, or reject this case?",
        ],
        start=1,
    ):
        steps.append(Prompt.ask(f"Step {index}", default=default))

    tools = [
        ToolSpec(name="lookup_case_context", description="Look up customer, site, or case context.", category="context"),
        ToolSpec(name="update_case_memory", description="Update memory with learnings from this case.", category="memory"),
    ]
    if Confirm.ask("Does this agent need to ask humans for missing information?", default=True):
        tools.append(
            ToolSpec(
                name="send_clarification_request",
                description="Draft a clarification request as a pending action.",
                category="communication",
                sandbox=True,
            )
        )

    knowledge_collections: list[KnowledgeCollectionSpec] = []
    if Confirm.ask("Does this agent need books or reference documents?", default=True):
        collection_name = Prompt.ask("Knowledge collection slug", default=f"{name}-books")
        collection_description = Prompt.ask(
            "Knowledge collection description",
            default=f"Reference books and documents for {role}.",
        )
        knowledge_collections.append(
            KnowledgeCollectionSpec(
                name=collection_name,
                description=collection_description,
                books_dir=f"knowledge/books/{collection_name}",
            )
        )

    example = ExampleCaseSpec(
        title="Typical case",
        input_summary=Prompt.ask("Describe a typical case", default=f"A normal {case_type} with enough details."),
        chain_of_thought=Prompt.ask(
            "How does the expert think through it?",
            default="Classify the request, inspect context, check constraints, then complete the work product.",
        ),
        outcome="complete",
    )

    output_field = SchemaFieldSpec(
        name="domain_output",
        type="dict",
        description=Prompt.ask("What final work product should be returned?", default="Structured expert work product."),
        required=False,
    )

    return AgentSpec(
        name=name,
        description=description,
        identity=AgentIdentity(role=role, domain=domain, years_experience=years, mindset=mindset),
        case_type=case_type,
        chain_of_thought_steps=steps,
        tools=tools,
        knowledge_collections=knowledge_collections,
        outcomes=[
            OutcomeSpec(name="complete", description="The expert can finish the work product."),
            OutcomeSpec(name="needs_clarification", description="A human must provide missing facts."),
            OutcomeSpec(name="rejected", description="The input is defective or unusable."),
        ],
        output_fields=[output_field],
        example_cases=[example],
    )


async def _agentic_interview(console: Console) -> AgentSpec:
    """Run an LLM-powered conversational Brain Clone interview."""

    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart

    settings = Settings.from_env()
    model = _build_model(settings.default_model, settings)

    resumed_name = _check_existing_session(console)

    console.print()
    console.print(Panel(
        "[bold white]Agent2 Brain Clone[/bold white]\n"
        "[#9A9590]Adaptive interview powered by your selected model.[/]\n\n"
        "The AI interviewer will ask you about your professional expertise\n"
        "and build a production agent from your answers.\n\n"
        "[#777]Type your answers naturally. Type 'done' to finish early.\n"
        "Type 'quit' to cancel.[/]",
        border_style="#FF3B30",
        padding=(1, 2),
    ))
    console.print()

    agent: Agent[None, str] = Agent(
        model,
        output_type=str,
        instructions=_get_interview_prompt(),
    )

    message_history: list[ModelMessage] = []
    spec: AgentSpec | None = None
    turn = 0
    max_turns = 40

    while turn < max_turns:
        turn += 1

        if turn == 1:
            user_text = "(The expert has just sat down. Begin the interview.)"
        else:
            console.print()
            try:
                user_text = Prompt.ask("[bold cyan]You[/bold cyan]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Interview cancelled.[/dim]")
                raise KeyboardInterrupt

            if user_text.strip().lower() == "quit":
                console.print("[dim]Interview cancelled.[/dim]")
                raise KeyboardInterrupt

            if user_text.strip().lower() == "done":
                user_text = (
                    "I think you have enough information now. Please finalize the "
                    "agent specification. Say INTERVIEW_COMPLETE and output the JSON."
                )

        try:
            result = await agent.run(user_text, message_history=message_history)
        except Exception as exc:
            error_msg = str(exc)
            if "401" in error_msg or "auth" in error_msg.lower():
                console.print("\n[bold red]LLM authentication failed.[/bold red] Check your OpenRouter API key.")
                console.print("[dim]Falling back to static questionnaire...[/dim]\n")
                return _questionnaire(console)
            console.print(f"\n[bold red]LLM error:[/bold red] {error_msg}")
            if turn == 1:
                console.print("[dim]Falling back to static questionnaire...[/dim]\n")
                return _questionnaire(console)
            console.print("[dim]Retrying...[/dim]")
            continue
        message_history = result.all_messages()

        response_text = result.output
        phase = _detect_phase(response_text, turn)
        console.print()
        console.print(Rule(style="#333333"))
        console.print(Panel(
            Markdown(response_text),
            title=f"[bold #FF3B30]Brain Clone[/bold #FF3B30] [#9A9590]{phase}[/]",
            border_style="#252525",
            padding=(0, 1),
        ))

        _save_interview_session(
            resumed_name or "in-progress",
            _detect_phase_number(response_text, turn),
            message_history,
            console,
        )

        if "INTERVIEW_COMPLETE" in response_text:
            spec = _extract_spec_from_response(response_text, console)
            if spec is not None:
                _clear_session(resumed_name or "in-progress")
                _clear_session(spec.name)
                break
            console.print("[yellow]Could not parse the agent spec. Continuing interview...[/yellow]")
            message_history.append(
                ModelRequest(parts=[UserPromptPart(content=(
                    "The JSON you produced could not be parsed into a valid AgentSpec. "
                    "Please try again: output INTERVIEW_COMPLETE followed by valid JSON."
                ))])
            )

    if spec is None:
        console.print("[bold red]Interview did not produce a valid spec after max turns.[/bold red]")
        console.print("[dim]Falling back to static questionnaire.[/dim]")
        return _questionnaire(console)

    console.print()
    console.print(Panel(
        f"[bold white]Agent:[/bold white] [#FF3B30]{spec.name}[/]\n"
        f"[bold white]Role:[/bold white] {spec.identity.role} ({spec.identity.years_experience}y in {spec.identity.domain})\n"
        f"[bold white]Case:[/bold white] {spec.case_type}\n"
        f"[bold white]Tools:[/bold white] {', '.join(t.name for t in spec.tools) or 'default set'}\n"
        f"[bold white]Books:[/bold white] {', '.join(c.name for c in spec.knowledge_collections) or 'none'}\n"
        f"[bold white]Outcomes:[/bold white] {', '.join(o.name for o in spec.outcomes)}\n"
        f"[bold white]Chain-of-Thought:[/bold white] {len(spec.chain_of_thought_steps)} steps",
        title="[bold #FF3B30]●[/bold #FF3B30] [bold]Agent Spec[/bold]",
        border_style="#252525",
        padding=(1, 2),
    ))

    if not Confirm.ask("\n[bold]Generate this agent?[/bold]", default=True):
        console.print("[#777]Cancelled. No files written.[/]")
        raise KeyboardInterrupt

    return spec


def _extract_spec_from_response(text: str, console: Console) -> AgentSpec | None:
    """Try to extract a valid AgentSpec JSON from the interview response."""

    import re

    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not json_match:
        json_match = re.search(r"INTERVIEW_COMPLETE\s*\n?\s*(\{.*)", text, re.DOTALL)
    if not json_match:
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            json_str = text[brace_start:brace_end + 1]
        else:
            return None
    else:
        json_str = json_match.group(1)

    try:
        data = json.loads(json_str)
        _normalize_spec_data(data)
        return AgentSpec.model_validate(data)
    except Exception as exc:
        console.print(f"[dim]Spec parse error: {exc}[/dim]")
        return None


_ALLOWED_FIELD_TYPES = {"str", "int", "float", "bool", "list[str]", "dict"}


def _normalize_spec_data(data: dict) -> None:
    """Fix common LLM-generated spec deviations before Pydantic validation."""

    for field in data.get("output_fields", []):
        t = field.get("type", "str")
        if t not in _ALLOWED_FIELD_TYPES:
            if t.startswith("list"):
                field["type"] = "list[str]"
            elif t.startswith("dict"):
                field["type"] = "dict"
            else:
                field["type"] = "str"

    for tool in data.get("tools", []):
        name = tool.get("name", "")
        tool["name"] = name.replace("-", "_").replace(" ", "_")

    name = data.get("name", "")
    data["name"] = name.replace("_", "-").replace(" ", "-").lower()


_PHASE_KEYWORDS = [
    (["role", "experience", "professional", "what do you do", "how long"], "Phase 1/8 · Identity", 1),
    (["thinking", "chain", "step by step", "walk me through", "first thought", "process"], "Phase 2/8 · Thinking", 2),
    (["premise", "confirm", "assumption", "building the agent on", "wrong in production"], "Phase 2.5/8 · Premises", 3),
    (["tool", "desk", "reference", "database", "software", "workspace", "browser", "tabs"], "Phase 3/8 · Tools", 3),
    (["book", "manual", "regulation", "document", "knowledge", "collection"], "Phase 4/8 · Knowledge", 4),
    (["example", "case", "typical", "recent", "scenario", "rejected", "clarification"], "Phase 5/8 · Examples", 5),
    (["output", "work product", "format", "confidence", "final", "deliver"], "Phase 6/8 · Output", 6),
    (["scope", "smallest version", "one agent or", "approval", "separate"], "Phase 6.5/8 · Scope", 7),
]


def _detect_phase_number(response: str, turn: int) -> int:
    """Return a numeric phase estimate (1-8) based on response content."""
    lower = response.lower()
    for keywords, _label, number in _PHASE_KEYWORDS:
        matches = sum(1 for kw in keywords if kw in lower)
        if matches >= 2:
            return number
    if turn <= 2:
        return 1
    return min(turn, 8)


def _detect_phase(response: str, turn: int) -> str:
    """Return a human-readable phase label for the interview panel."""
    lower = response.lower()
    for keywords, label, _number in _PHASE_KEYWORDS:
        matches = sum(1 for kw in keywords if kw in lower)
        if matches >= 2:
            return label
    if turn <= 2:
        return "Phase 1/8 · Identity"
    return f"Turn {turn}"


async def _polish_spec_with_llm(spec: AgentSpec) -> AgentSpec:
    """Let an LLM improve the spec while still returning validated AgentSpec."""

    try:
        from pydantic_ai import Agent

        settings = Settings.from_env()
        model = _build_model(settings.default_model, settings)
        agent = Agent(model, output_type=AgentSpec, instructions=BRAIN_CLONE_SYNTHESIS_PROMPT)
        result = await agent.run(spec.model_dump_json(indent=2))
        return result.output
    except Exception:
        return spec


def textual_available() -> bool:
    """Return True when Textual can be imported."""

    try:
        import textual  # noqa: F401

        return True
    except Exception:
        return False


def _tui_questionnaire() -> AgentSpec:
    from agent2_cli.tui import run_brain_clone_tui

    return run_brain_clone_tui()
