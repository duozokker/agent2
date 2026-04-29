"""Brain Clone onboarding flow for Agent2."""

from __future__ import annotations

import asyncio
import json
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

AGENTIC_INTERVIEW_PROMPT = """\
You are the Agent2 Brain Clone interviewer. Your job is to interview a domain
expert and extract everything needed to build a production AI agent that clones
their professional brain.

You conduct an adaptive, conversational interview across these phases:

## Phase 1: Identity
Understand WHO this expert is. Ask about their role, years of experience, domain,
what separates them from a beginner, and their work style. Be natural — ask
follow-up questions based on their answers.

## Phase 2: Thinking Process (MOST IMPORTANT)
Extract the expert's ACTUAL Sachbearbeiter Chain-of-Thought. Ask them to walk
through a recent case step by step. Push for specifics — do NOT accept vague
answers like "I analyze it". Ask: "What exactly do you check first? Then what?
When do you hesitate? When do you look something up vs trust your memory?"

## Phase 3: Tools and Workspace
Map their real-world tools to categories. Ask: "What's on your desk? Which
reference books do you use? What databases? Do you keep personal notes? When do
you search the internet? Do you send emails as part of work?"

## Phase 4: Knowledge and Reference Material
Identify what goes into knowledge books. Ask: "Which books, manuals, or
regulations are essential? If you could keep only 3 reference books, which ones?"

## Phase 5: Example Cases
Collect 2-3 diverse cases. Ask for: a typical case, one where they asked for
clarification, and one they rejected. For each, capture the thinking chain.

## Phase 6: Output Format
Ask: "When you finish a case, what does the work product look like? What fields
must always be present? How do you express confidence?"

## Interview Rules
- Ask ONE question at a time. Wait for the answer before the next question.
- Adapt your questions based on their answers — this is a conversation, not a form.
- Use the expert's domain language, not generic AI terminology.
- When you have enough information for a phase, naturally transition to the next.
- Be warm and professional. The expert should feel like they're talking to a
  colleague who genuinely wants to understand their work.
- After Phase 6, briefly summarize what you've learned and ask if anything is missing.
- When the expert confirms OR says "done", "that's it", "nothing else", or similar,
  immediately finalize. Do NOT ask additional clarifying questions after the user
  signals completion.
- When finalizing, say exactly: "INTERVIEW_COMPLETE" on its own line,
  followed by the collected data as a structured JSON block.
- If the user provides very detailed answers, you can skip ahead — don't pad the
  interview artificially. 6-10 turns total is ideal.

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
    out.print(f"\n[bold green]Generated {spec.name}[/bold green] at {agent_dir}")
    out.print(f"Run locally: [cyan]uv run agent2 serve {spec.name}[/cyan]")
    out.print(f"Agent API port in config: [cyan]{spec.port}[/cyan]")
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

    console.print()
    console.print(Panel(
        "[bold white]Agent2 Brain Clone[/bold white]\n"
        "[dim]Adaptive interview powered by your selected model.[/dim]\n\n"
        "The AI interviewer will ask you about your professional expertise\n"
        "and build a production agent from your answers.\n\n"
        "[dim italic]Type your answers naturally. Type 'done' to finish early.\n"
        "Type 'quit' to cancel.[/dim italic]",
        border_style="#ff5a4f",
        padding=(1, 2),
    ))
    console.print()

    agent: Agent[None, str] = Agent(
        model,
        output_type=str,
        instructions=AGENTIC_INTERVIEW_PROMPT,
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
        console.print()
        console.print(Rule(style="#333333"))
        console.print(Panel(
            Markdown(response_text),
            title="[bold #ff5a4f]Brain Clone Interviewer[/bold #ff5a4f]",
            border_style="#333333",
            padding=(0, 1),
        ))

        if "INTERVIEW_COMPLETE" in response_text:
            spec = _extract_spec_from_response(response_text, console)
            if spec is not None:
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
        f"[bold]Agent:[/bold] {spec.name}\n"
        f"[bold]Role:[/bold] {spec.identity.role} ({spec.identity.years_experience}y in {spec.identity.domain})\n"
        f"[bold]Case type:[/bold] {spec.case_type}\n"
        f"[bold]Tools:[/bold] {', '.join(t.name for t in spec.tools) or 'default set'}\n"
        f"[bold]Knowledge:[/bold] {', '.join(c.name for c in spec.knowledge_collections) or 'none'}\n"
        f"[bold]Outcomes:[/bold] {', '.join(o.name for o in spec.outcomes)}\n"
        f"[bold]Chain-of-Thought:[/bold] {len(spec.chain_of_thought_steps)} steps",
        title="[bold green]Generated Agent Spec[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    if not Confirm.ask("\n[bold]Generate this agent?[/bold]", default=True):
        console.print("[dim]Cancelled. No files written.[/dim]")
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
