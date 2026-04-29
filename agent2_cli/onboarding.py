"""Brain Clone onboarding flow for Agent2."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

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
    console: Console | None = None,
) -> Path:
    """Run onboarding and generate an Agent2 agent."""

    out = console or Console()
    if from_spec is not None:
        spec = load_spec(from_spec)
    else:
        spec = _tui_questionnaire() if use_tui and textual_available() else _questionnaire(out)
        if not no_llm and Settings.from_env().has_llm_key:
            spec = asyncio.run(_polish_spec_with_llm(spec))

    agent_dir = generate_agent_from_spec(spec, project_root=project_root, overwrite=overwrite)
    out.print(f"[bold green]Generated {spec.name}[/bold green] at {agent_dir}")
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
