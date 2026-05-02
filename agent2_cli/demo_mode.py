"""Simulated Brain Clone interview for demo recordings.

Plays back a pre-scripted interview with typing animations so the
user can record a video without needing to type live. Uses the
procurement-compliance-officer fixture.
"""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule

from agent2_cli.generator import generate_agent_from_spec
from agent2_cli.spec import AgentSpec

MONO = "'JetBrains Mono', ui-monospace, monospace"

DEMO_INTERVIEW = [
    {
        "phase": "Phase 1/6 · Identity",
        "question": "Welcome! Let's start at the beginning. What's your professional role, and how long have you been doing it?",
        "answer": "Procurement compliance officer, 12 years. I review purchase requests and decide if they follow company policy before approval.",
    },
    {
        "phase": "Phase 2/6 · Thinking",
        "question": "Walk me through exactly what happens when a purchase request lands on your desk. Step by step — what do you check first?",
        "answer": "Step by step: I check the requester and department. Then the amount — over 25k needs a competitive quote. I look up the vendor in our risk database. Check the business justification. Then decide: approve, ask for clarification, or reject.",
    },
    {
        "phase": "Phase 3/6 · Tools",
        "question": "What tools and systems do you reach for while doing this? Databases, reference books, communication channels?",
        "answer": "I use our company procurement policy handbook, vendor risk guidelines, and approval threshold tables. I also check purchase history for the vendor. For communication, I email requesters when I need clarification.",
    },
    {
        "phase": "Phase 4/6 · Knowledge",
        "question": "Which reference materials are essential? If you could only keep 3 on your desk, which ones?",
        "answer": "The procurement policy handbook is number one. Then vendor risk guidelines. And the approval threshold tables — those tell me who needs to sign off at each amount level.",
    },
    {
        "phase": "Phase 5/6 · Examples",
        "question": "Give me a typical case you'd approve, one you'd send back for clarification, and one you'd reject outright.",
        "answer": "Approve: 50 laptops from a known vendor, 42k, clear justification, department head signs off. Clarify: sole-source software renewal with no rationale for why no competitive quote. Reject: purchase from a vendor flagged as blocked in our risk database.",
    },
    {
        "phase": "Phase 6/6 · Output",
        "question": "When you finish reviewing a request, what does your decision look like? What information does it always include?",
        "answer": "Always one of three outcomes: approved, needs clarification, or rejected. With the reasoning, which policies I checked, required approvals, and any conditions or next actions. Confidence is high when all info is present, lower for new vendors.",
    },
]

DEMO_SPEC_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "roofing-agent-spec.json"

PROCUREMENT_SPEC = {
    "name": "procurement-compliance-officer",
    "description": "Reviews purchase requests against company procurement policies. Approves, requests clarification, or rejects based on structured compliance review.",
    "identity": {
        "role": "Procurement Compliance Officer",
        "domain": "corporate procurement and vendor management",
        "years_experience": 12,
        "mindset": "Rules-first, structured, holds requests until satisfied rather than approving under uncertainty.",
    },
    "case_type": "purchase request",
    "chain_of_thought_steps": [
        "Identify requester and department — is this person authorized?",
        "Check amount against approval thresholds — under 25k is standard, above needs competitive quote",
        "Look up vendor in risk database — approved, unapproved, or blocked?",
        "Evaluate business justification — specific and substantiated?",
        "Check purchase history for this vendor and department",
        "Determine outcome: approve with conditions, request clarification, or reject",
        "Document reasoning, policies checked, and required next actions",
    ],
    "tools": [
        {"name": "lookup_vendor", "description": "Look up vendor status in risk database", "category": "context", "sandbox": False},
        {"name": "get_approval_thresholds", "description": "Get approval threshold for department and amount", "category": "knowledge", "sandbox": False},
        {"name": "search_policy", "description": "Search procurement policy handbook", "category": "knowledge", "sandbox": False},
        {"name": "get_purchase_history", "description": "Get past purchases for vendor or department", "category": "context", "sandbox": False},
        {"name": "get_requester_info", "description": "Look up requester authorization and department", "category": "context", "sandbox": False},
        {"name": "send_clarification_request", "description": "Send clarification email to requester", "category": "communication", "sandbox": True},
        {"name": "save_decision_record", "description": "Save final decision to procurement system", "category": "record", "sandbox": True},
    ],
    "knowledge_collections": [
        {"name": "procurement-policy", "description": "Company procurement policy handbook", "books_dir": "knowledge/books/procurement-policy"},
        {"name": "vendor-risk-guidelines", "description": "Vendor risk assessment and blocked vendor criteria", "books_dir": "knowledge/books/vendor-risk-guidelines"},
        {"name": "approval-thresholds", "description": "Approval threshold tables by department and amount", "books_dir": "knowledge/books/approval-thresholds"},
    ],
    "outcomes": [
        {"name": "approved", "description": "Request is policy-compliant and complete"},
        {"name": "needs_clarification", "description": "Missing information that a human must provide"},
        {"name": "rejected", "description": "Policy violation, blocked vendor, or fabricated documentation"},
    ],
    "output_fields": [
        {"name": "domain_output", "type": "dict", "description": "Approval record with conditions, or rejection with cited policy", "required": False},
    ],
    "example_cases": [
        {"title": "Standard laptop purchase — approved", "input_summary": "50 laptops, known vendor, $42k, clear justification", "chain_of_thought": "Vendor approved, amount needs dept head + finance sign-off, justification clear. Approve with conditions.", "outcome": "approved"},
        {"title": "Sole-source software — needs clarification", "input_summary": "Software renewal, $38k, no competitive quote, no sole-source rationale", "chain_of_thought": "Missing sole-source justification. Cannot approve without rationale. Ask for missing info.", "outcome": "needs_clarification"},
        {"title": "Blocked vendor — rejected", "input_summary": "Office supplies from vendor flagged in risk database", "chain_of_thought": "Vendor is blocked. Immediate rejection, no further review needed.", "outcome": "rejected"},
    ],
    "port": 8050,
}


def _type_text(console: Console, text: str, speed: float = 0.02) -> None:
    """Simulate typing with character-by-character output."""
    for char in text:
        console.print(char, end="", highlight=False)
        time.sleep(speed)
    console.print()


def run_demo_interview(*, project_root: Path, overwrite: bool = False, console: Console) -> None:
    """Run a simulated Brain Clone interview for demo recording."""

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

    for i, step in enumerate(DEMO_INTERVIEW):
        console.print()
        console.print(Rule(style="#333333"))
        console.print(Panel(
            Markdown(step["question"]),
            title=f"[bold #FF3B30]Brain Clone[/bold #FF3B30] [#9A9590]{step['phase']}[/]",
            border_style="#252525",
            padding=(0, 1),
        ))

        console.print()
        console.print("[bold cyan]You[/bold cyan]", end=" ")

        Prompt.ask("", default="")
        # User presses Enter, then we "type" the answer
        console.print("[bold cyan]You[/bold cyan] ", end="")
        _type_text(console, step["answer"], speed=0.015)

        time.sleep(0.5)

    # Generate the agent
    console.print()
    console.print(Rule(style="#333333"))
    console.print("[bold]  Generating agent from interview...[/bold]")
    time.sleep(1)

    spec = AgentSpec.model_validate(PROCUREMENT_SPEC)
    agent_dir = generate_agent_from_spec(spec, project_root=project_root, overwrite=overwrite)

    console.print()
    console.print(Panel(
        f"[bold white]Agent:[/bold white] [#FF3B30]{spec.name}[/]\n"
        f"[bold white]Role:[/bold white] {spec.identity.role} ({spec.identity.years_experience}y)\n"
        f"[bold white]Tools:[/bold white] {len(spec.tools)} ({', '.join(t.name for t in spec.tools[:4])}...)\n"
        f"[bold white]Knowledge:[/bold white] {len(spec.knowledge_collections)} collections\n"
        f"[bold white]Chain-of-Thought:[/bold white] {len(spec.chain_of_thought_steps)} steps\n"
        f"[bold white]Examples:[/bold white] {len(spec.example_cases)} cases",
        title="[bold #FF3B30]●[/bold #FF3B30] [bold]Agent Generated[/bold]",
        border_style="#252525",
        padding=(1, 2),
    ))

    console.print()
    console.print(Panel(
        f"[green]✓[/green] Generated [bold]{spec.name}[/bold] at {agent_dir}\n\n"
        f"[bold white]Your agent will run at:[/bold white]\n"
        f"  [#FF3B30]http://localhost:{spec.port}[/]\n\n"
        f"[bold white]Test it:[/bold white]\n"
        f"  uv run agent2 serve {spec.name}\n"
        f"  uv run agent2 run {spec.name} --text \"Purchase request: 50 laptops, $42k\"",
        title="[bold #FF3B30]●[/bold #FF3B30] [bold]Agent Ready[/bold]",
        border_style="#252525",
        padding=(1, 2),
    ))
