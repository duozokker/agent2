"""Deterministic Agent2 agent generator for Brain Clone onboarding."""

from __future__ import annotations

import json
from pathlib import Path

from agent2_cli.spec import AgentSpec, class_name_from_slug


class GenerationError(RuntimeError):
    """Raised when an agent cannot be generated safely."""


def generate_agent_from_spec(spec: AgentSpec, *, project_root: Path | None = None, overwrite: bool = False) -> Path:
    """Generate a complete Agent2 agent from a validated spec."""

    root = project_root or Path.cwd()
    agent_dir = root / "agents" / spec.name
    if agent_dir.exists() and not overwrite:
        raise GenerationError(f"Agent '{spec.name}' already exists. Pass overwrite=True to replace it.")

    agent_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = root / "tests" / "generated_agents"
    tests_dir.mkdir(parents=True, exist_ok=True)
    eval_dir = root / "tests" / "promptfoo" / spec.name
    eval_dir.mkdir(parents=True, exist_ok=True)

    files = {
        agent_dir / "__init__.py": "",
        agent_dir / "schemas.py": _render_schemas(spec),
        agent_dir / "tools.py": _render_tools(spec),
        agent_dir / "agent.py": _render_agent(spec),
        agent_dir / "config.yaml": _render_config(spec),
        agent_dir / "main.py": _render_main(spec),
        agent_dir / "Dockerfile": _render_dockerfile(spec),
        tests_dir / f"test_{spec.name.replace('-', '_')}.py": _render_test(spec),
        eval_dir / "dataset.json": _render_eval_dataset(spec),
        eval_dir / "eval.yaml": _render_eval_config(spec),
    }
    for collection in spec.knowledge_collections:
        books_dir = root / (collection.books_dir or f"knowledge/books/{collection.name}")
        files[books_dir / "README.md"] = _render_knowledge_readme(spec.name, collection.name, collection.description)

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return agent_dir


def _first_complete_outcome(spec: AgentSpec) -> str:
    for outcome in spec.outcomes:
        if outcome.name not in {"needs_clarification", "rejected"}:
            return outcome.name
    return "complete"


def _prompt(spec: AgentSpec) -> str:
    steps = "\n".join(f"- {step}" for step in spec.chain_of_thought_steps)
    tools = "\n".join(f"- {tool.name}(): {tool.description}" for tool in spec.tools) or "- note_review_step()"
    examples = "\n\n".join(
        f"{case.title}: {case.input_summary}. {case.chain_of_thought} Outcome: {case.outcome}."
        for case in spec.example_cases
    ) or "Routine case: classify the input, inspect context, decide whether to complete, clarify, or reject."
    outcomes = "\n".join(f"- {outcome.name}: {outcome.description}" for outcome in spec.outcomes)

    return f"""\
You are a senior {spec.identity.role} with {spec.identity.years_experience} years of experience in {spec.identity.domain}.
Mindset: {spec.identity.mindset}

Your job is to process one {spec.case_type} into exactly one structured outcome.

## Your Workspace

You sit at your desk with these tools:

{tools}

Use tools naturally, like a human expert. Do not call every tool mechanically.

## Sachbearbeiter Chain of Thought

When a {spec.case_type} lands on your desk, run the expert Chain-of-Thought:

{steps}

Use note_review_step() for visible checkpoints when the case is complex.

## Example Chains of Thought

{examples}

## Three Outcomes

{outcomes}

## Output Format

Return the declared schema only. Keep reasoning concise and operational. Use
review_steps[] for visible professional checkpoints, not an exhaustive hidden transcript.
"""


def _render_schemas(spec: AgentSpec) -> str:
    class_prefix = class_name_from_slug(spec.name)
    status_values = ", ".join(repr(outcome.name) for outcome in spec.outcomes)
    complete = _first_complete_outcome(spec)
    extra_fields = "\n".join(
        f"    {field.name}: {_python_type(field.type)} | None = Field(default=None, description={field.description!r})"
        for field in spec.output_fields
    )
    if not extra_fields:
        extra_fields = "    domain_output: dict | None = Field(default=None, description='Structured work product when complete.')"

    return f'''"""Structured output schemas for the generated {spec.name} agent."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class PendingAction(BaseModel):
    action: str
    params: dict = Field(default_factory=dict)
    description: str = ""


class ClarificationRequest(BaseModel):
    question: str
    missing_fields: list[str] = Field(default_factory=list)


class Extracted{class_prefix}Fields(BaseModel):
    raw_summary: str = ""
    source: str = "user_input"


class {class_prefix}Result(BaseModel):
    status: Literal[{status_values}]
    extracted_fields: Extracted{class_prefix}Fields
{extra_fields}
    clarification: ClarificationRequest | None = None
    rejection_reason: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    review_steps: list[str] = Field(default_factory=list)
    pending_actions: list[PendingAction] = Field(default_factory=list)
    needs_review: bool = False

    @model_validator(mode="after")
    def _check_status_consistency(self) -> Self:
        if self.status == "{complete}":
            if self.clarification is not None:
                raise ValueError("clarification must be empty when status is {complete}")
            if self.rejection_reason:
                raise ValueError("rejection_reason must be empty when status is {complete}")
        if self.status == "needs_clarification":
            if self.clarification is None:
                raise ValueError("clarification is required when status is needs_clarification")
            if self.rejection_reason:
                raise ValueError("rejection_reason must be empty when status is needs_clarification")
        if self.status == "rejected":
            if not self.rejection_reason:
                raise ValueError("rejection_reason is required when status is rejected")
            if self.clarification is not None:
                raise ValueError("clarification must be empty when status is rejected")
        return self
'''


def _python_type(field_type: str) -> str:
    return {
        "str": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "list[str]": "list[str]",
        "dict": "dict",
    }.get(field_type, "str")


def _render_tools(spec: AgentSpec) -> str:
    tool_functions = []
    for tool in spec.tools:
        tool_functions.append(
            f'''
async def {tool.name}(**kwargs: Any) -> dict[str, Any]:
    """{tool.description}"""
    return {{
        "tool": "{tool.name}",
        "sandbox": {tool.sandbox!r},
        "received": kwargs,
        "note": "Generated stub. Replace with a real integration when ready.",
    }}
'''
        )
    custom_tools = "\n".join(tool_functions)
    return f'''"""Generated tool stubs for the {spec.name} agent."""

from __future__ import annotations

from typing import Any

_MEMORY: dict[str, str] = {{}}
_RESULTS: dict[str, dict[str, Any]] = {{}}


async def note_review_step(step: str, finding: str, next_action: str = "") -> dict[str, Any]:
    """Record a visible checkpoint in the expert Chain-of-Thought."""
    return {{"recorded": True, "step": step, "finding": finding, "next_action": next_action}}


async def get_context_info(context_id: str = "default") -> dict[str, Any]:
    """Load generated demo context and memory."""
    return {{"context_id": context_id, "memory": _MEMORY.get(context_id, "")}}


async def update_context_memory(context_id: str, memory: str) -> dict[str, Any]:
    """Update demo memory for this generated agent."""
    _MEMORY[context_id] = memory[:10_000]
    return {{"updated": True, "context_id": context_id}}


async def request_clarification(question: str, missing_fields: list[str] | None = None) -> dict[str, Any]:
    """Return a pending clarification action."""
    return {{
        "pending": True,
        "action": "request_clarification",
        "params": {{"question": question, "missing_fields": missing_fields or []}},
        "description": question,
    }}


async def create_completion_record(case_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Return a pending completion-record action."""
    return {{
        "pending": True,
        "action": "create_completion_record",
        "params": {{"case_id": case_id, "result": result}},
        "description": f"Create completion record for {{case_id}}",
    }}


async def record_case_result(job_id: str, output: dict[str, Any]) -> None:
    """Persist generated demo output in memory."""
    _RESULTS[job_id] = output
{custom_tools}
'''


def _render_agent(spec: AgentSpec) -> str:
    class_prefix = class_name_from_slug(spec.name)
    complete = _first_complete_outcome(spec)
    prompt = _prompt(spec)
    tool_regs = []
    for tool in spec.tools:
        tool_regs.append(
            f'''
@agent.tool_plain
async def {tool.name}(**kwargs: Any) -> dict[str, Any]:
    """{tool.description}"""
    return await tools.{tool.name}(**kwargs)
'''
        )
    custom_regs = "\n".join(tool_regs)
    return f'''"""Generated Brain Clone agent for {spec.name}."""

from __future__ import annotations

from typing import Any

from shared.action_executor import ActionRegistry
from shared.runtime import create_agent

from . import tools
from .schemas import {class_prefix}Result


SYSTEM_PROMPT = {prompt!r}

agent = create_agent(
    name="{spec.name}",
    output_type={class_prefix}Result,
    instructions=SYSTEM_PROMPT,
    toolsets=[],
)

action_registry = ActionRegistry()


async def _dry_run_action(action: dict[str, Any]) -> dict[str, Any]:
    return {{"executed": True, "dry_run": True, "params": action.get("params", {{}})}}


action_registry.register("request_clarification", _dry_run_action)
action_registry.register("create_completion_record", _dry_run_action)


async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
    """Execute approved sandbox actions in dry-run mode."""
    return await action_registry.execute(action)


@agent.tool_plain
async def note_review_step(step: str, finding: str, next_action: str = "") -> dict[str, Any]:
    """Record a visible checkpoint in the expert Chain-of-Thought."""
    return await tools.note_review_step(step, finding, next_action)


@agent.tool_plain
async def get_context_info(context_id: str = "default") -> dict[str, Any]:
    """Load context details and memory for this case."""
    return await tools.get_context_info(context_id)


@agent.tool_plain
async def update_context_memory(context_id: str, memory: str) -> dict[str, Any]:
    """Update memory with learnings from this case."""
    return await tools.update_context_memory(context_id, memory)


@agent.tool_plain
async def request_clarification(question: str, missing_fields: list[str] | None = None) -> dict[str, Any]:
    """Create a pending clarification action."""
    return await tools.request_clarification(question, missing_fields)


@agent.tool_plain
async def create_completion_record(case_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Create a pending completion-record action."""
    return await tools.create_completion_record(case_id, result)
{custom_regs}

def before_run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Inject resume instructions for continued cases."""
    if input_data.get("message_history"):
        input_data["_instructions"] = SYSTEM_PROMPT + "\\n\\nResume the existing case. Incorporate the human answer and finish."
    return input_data


def mock_result(input_data: dict[str, Any]) -> dict[str, Any]:
    """Schema-valid development response when no LLM key is configured."""
    raw = str(input_data.get("text") or input_data.get("case") or "")
    if not raw:
        return {{
            "status": "needs_clarification",
            "extracted_fields": {{"raw_summary": "", "source": "mock"}},
            "domain_output": None,
            "clarification": {{"question": "Please provide the case details.", "missing_fields": ["case"]}},
            "rejection_reason": None,
            "confidence": 0.45,
            "reasoning": "Mock mode found no case details.",
            "review_steps": ["Intake", "Missing case details", "Ask clarification"],
            "pending_actions": [
                {{
                    "action": "request_clarification",
                    "params": {{"question": "Please provide the case details.", "missing_fields": ["case"]}},
                    "description": "Ask for missing case details",
                }}
            ],
            "needs_review": False,
        }}
    return {{
        "status": "{complete}",
        "extracted_fields": {{"raw_summary": raw[:240], "source": "mock"}},
        "domain_output": {{"summary": "Generated mock work product for {spec.identity.role}."}},
        "clarification": None,
        "rejection_reason": None,
        "confidence": 0.82,
        "reasoning": "Mock mode produced a complete generated-agent result.",
        "review_steps": ["Intake", "Run Sachbearbeiter Chain-of-Thought", "Prepare completion record"],
        "pending_actions": [
            {{
                "action": "create_completion_record",
                "params": {{"case_id": input_data.get("case_id", "mock-case"), "result": {{"status": "{complete}"}}}},
                "description": "Create completion record",
            }}
        ],
        "needs_review": True,
    }}


async def after_run(input_data: dict[str, Any], output: dict[str, Any]) -> None:
    """Persist demo job output and mark low-confidence completions for review."""
    if output.get("status") == "{complete}" and float(output.get("confidence", 0.0)) < 0.85:
        output["needs_review"] = True
    if input_data.get("job_id"):
        await tools.record_case_result(str(input_data["job_id"]), output)
'''


def _render_config(spec: AgentSpec) -> str:
    collections = "\n".join(f"  - {collection.name}" for collection in spec.knowledge_collections)
    collections_block = "[]" if not collections else "\n" + collections
    return f'''name: {spec.name}
description: {json.dumps(spec.description)}
model: ""
port: {spec.port}
timeout_seconds: 300
max_retries: 3
collections: {collections_block}
provider_order: []
provider_policy: {{}}
capabilities:
  - resume
  - approval_workflow
'''


def _render_main(spec: AgentSpec) -> str:
    return f'''"""FastAPI entrypoint for {spec.name}."""

from shared.api import create_app

app = create_app("{spec.name}")
'''


def _render_dockerfile(spec: AgentSpec) -> str:
    return f'''FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY agent2.yaml ./agent2.yaml
COPY shared/ ./shared/
COPY agents/{spec.name}/ ./agent/
RUN mkdir -p agents/{spec.name} && cp agent/config.yaml agents/{spec.name}/config.yaml

RUN uv sync --no-dev

ENV PYTHONPATH=/app
ENV AGENT_NAME={spec.name}

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''


def _render_test(spec: AgentSpec) -> str:
    class_prefix = class_name_from_slug(spec.name)
    complete = _first_complete_outcome(spec)
    return f'''"""Generated smoke tests for {spec.name}."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_agent_module():
    root = Path(__file__).resolve().parents[2]
    package = "_generated_{spec.name.replace("-", "_")}"
    agent_dir = root / "agents" / "{spec.name}"
    init_spec = importlib.util.spec_from_file_location(package, agent_dir / "__init__.py", submodule_search_locations=[str(agent_dir)])
    assert init_spec and init_spec.loader
    init_module = importlib.util.module_from_spec(init_spec)
    sys.modules[package] = init_module
    init_spec.loader.exec_module(init_module)
    agent_spec = importlib.util.spec_from_file_location(f"{{package}}.agent", agent_dir / "agent.py")
    assert agent_spec and agent_spec.loader
    module = importlib.util.module_from_spec(agent_spec)
    sys.modules[agent_spec.name] = module
    agent_spec.loader.exec_module(module)
    return module


def test_generated_mock_result_is_schema_valid():
    module = _load_agent_module()
    result = module.mock_result({{"case": "Repair roof leak before heavy rain.", "case_id": "case-1"}})
    parsed = module.{class_prefix}Result.model_validate(result)
    assert parsed.status == "{complete}"
'''


def _render_eval_dataset(spec: AgentSpec) -> str:
    data = [
        {
            "vars": {
                "input": {
                    "case": spec.example_cases[0].input_summary if spec.example_cases else f"Example {spec.case_type}",
                    "case_id": "eval-case-1",
                }
            },
            "assert": [{"type": "contains-json"}],
        }
    ]
    return json.dumps(data, indent=2) + "\n"


def _render_eval_config(spec: AgentSpec) -> str:
    return f'''description: "Generated eval starter for {spec.name}"
providers:
  - id: http
    config:
      url: "http://localhost:{spec.port}/tasks?mode=sync"
      method: POST
      headers:
        Authorization: "Bearer {{{{env.AGENT_TOKEN}}}}"
        Content-Type: application/json
      body:
        input: "{{{{input}}}}"
prompts:
  - "{{{{input}}}}"
tests: file://dataset.json
'''


def _render_knowledge_readme(agent_name: str, collection_name: str, description: str) -> str:
    return f"""# {collection_name}

{description}

Add source documents for `{agent_name}` here. Prefer real policies, manuals,
SOPs, examples, checklists, and expert-written notes over hardcoded lookup
tables in the prompt.
"""
