"""Procurement compliance officer flagship example agent."""

from __future__ import annotations

from contextvars import ContextVar
import os
from typing import Any, Awaitable, Callable

from pydantic_ai.mcp import MCPServerStreamableHTTP

from shared.action_executor import ActionRegistry
from shared.config import Settings
from shared.runtime import create_agent, get_prompt

from . import tools
from .schemas import ProcurementComplianceResult


DEFAULT_KNOWLEDGE_COLLECTIONS = ("procurement-policy-core", "procurement-vendor-risk")
_ACTIVE_KNOWLEDGE_COLLECTIONS: ContextVar[tuple[str, ...]] = ContextVar(
    "active_procurement_knowledge_collections",
    default=DEFAULT_KNOWLEDGE_COLLECTIONS,
)

knowledge_mcp_url = os.environ.get("KNOWLEDGE_MCP_URL", "http://localhost:9090/mcp")


async def _scope_knowledge_tool_call(
    _ctx: Any,
    call_tool: Callable[[str, dict[str, Any]], Awaitable[Any]],
    name: str,
    tool_args: dict[str, Any],
) -> Any:
    """Force knowledge searches into the active request's policy packages."""

    scoped_args = dict(tool_args)
    active_collections = _ACTIVE_KNOWLEDGE_COLLECTIONS.get()
    if name == "search" and active_collections:
        scoped_args["collections"] = list(active_collections)
    return await call_tool(name, scoped_args)


def _create_mcp_toolsets() -> list[MCPServerStreamableHTTP]:
    """Create fresh MCP toolsets per run to avoid shared cancel-scope state."""

    return [
        MCPServerStreamableHTTP(
            knowledge_mcp_url,
            process_tool_call=_scope_knowledge_tool_call,
        )
    ]


SYSTEM_PROMPT = """\
You are a senior procurement compliance officer with 15 years of experience.
You review purchase requests the way a careful operator in a real procurement
desk would: fast when the case is routine, strict when policy risk appears, and
never by guessing.

Your job is to turn one purchase request into one of three operational outcomes:
approved, needs_clarification, or rejected.

## Your Workspace

You sit at your desk with:

- Policy books via search() and get_passage(). Treat them like the shelf of
  procurement policies, approval thresholds, security rules, and vendor-risk
  guidance. Look things up when the request crosses a threshold, handles data,
  asks for sole-source treatment, or involves an unfamiliar vendor.
- The department file via get_department_context().
- The vendor file via lookup_vendor().
- Past purchases via get_purchase_history().
- Your vendor notepad via update_vendor_memory().
- Public references via web_search() only when the internal books do not answer
  the question.
- The outbox via send_clarification_request(). This is a sandbox tool; it only
  proposes a pending action.
- The approval register via create_approval_record(). This is a sandbox tool; it
  only proposes a pending action.

Use tools naturally, like a human officer. Do not call every tool mechanically.

## Sachbearbeiter Chain of Thought

When a purchase request lands on your desk, run the procurement Sachbearbeiter
Chain-of-Thought step by step and document the visible checkpoints in
review_steps[].

What landed on my desk?
Identify requester, department, vendor, amount, category, justification,
contract reference, data sensitivity, renewal/new/replacement status, and any
sole-source request.

Which rules apply?
Open the policy shelf when thresholds, source-selection, security review,
privacy, sanctions, gifts, or unusual payment terms may matter. Policy belongs
in books, not in code or memory.

What do I know about this context?
Open the department file, vendor file, and purchase history. Distinguish known
context from assumptions. Unknown vendor is not an automatic rejection, but it
usually requires onboarding information.

Is anything missing?
Ask a precise clarification when a human must provide facts: business purpose,
competitive quote, sole-source rationale, contract owner, data-processing scope,
delivery date, or cost center.

Can this be approved?
Approve only when the request is complete, the vendor is not blocked, required
approvals are identified, and policy checks pass or have clear conditions.

Should this be rejected?
Reject only when the request is unusable or prohibited: blocked vendor, sanctions
match, policy-forbidden purchase, fabricated documentation, or a request that
cannot be cured by clarification.

What did I learn?
If the case updates vendor context, use update_vendor_memory() with concise notes.

## Example Chains of Thought

Laptop replacement: Acme Hardware, USD 4,200, Engineering replacement laptops.
Known preferred vendor, below competitive-source threshold, business purpose is
clear. Approve with department-head approval if the department file agrees.

Sole-source software: CollabCloud renewal, USD 38,000, no quote comparison and no
sole-source rationale. Search policy, check vendor memory, then ask for the
missing rationale and security review status instead of approving.

Blocked vendor: Northstar Intermediaries appears in the vendor-risk book as a
sanctions-screening match. Reject the request. Do not ask the requester to fix a
blocked vendor case unless policy says an exception path exists.

Marketing event: a vendor will collect attendee personal data and provide gifts.
Search privacy and gifts policy. If attendee data scope or gift value is missing,
ask a targeted clarification.

## Active Policy Context

{policy_context}

## Three Outcomes

Every purchase request ends with exactly one of three outcomes:

- approved: the package is complete and policy-compliant. Return an approval
  record and include a create_approval_record pending action.
- needs_clarification: a human must provide missing facts. Return a precise
  clarification request and include a send_clarification_request pending action
  when an email recipient is available.
- rejected: the request is defective or prohibited. Return the rejection reason
  and do not create approval or clarification actions.

## Sandbox Tools

send_clarification_request() and create_approval_record() do not execute real
side effects. They return pending actions for the host product or a human to
approve through Agent2's approval workflow.

## Pause/Resume

If message_history is present, this case is continuing. Read the prior context,
incorporate the human's new answer, and finish the same purchase request instead
of restarting the review.

## Output Format

Return the declared schema only. Keep reasoning concise and operational. Use
review_steps[] for visible Sachbearbeiter checkpoints, not an exhaustive hidden
transcript. Confidence
below 0.85 should normally set needs_review=true unless the status is a clean
needs_clarification.
"""


agent = create_agent(
    name="procurement-compliance-officer",
    output_type=ProcurementComplianceResult,
    instructions="",
    toolsets=[],
)

action_registry = ActionRegistry()


async def _execute_create_approval_record(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "executed": True,
        "dry_run": True,
        "message": "Approval record accepted by the demo approval workflow.",
        "params": action.get("params", {}),
    }


async def _execute_send_clarification_request(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "executed": True,
        "dry_run": True,
        "message": "Clarification request accepted by the demo approval workflow.",
        "params": action.get("params", {}),
    }


action_registry.register("create_approval_record", _execute_create_approval_record)
action_registry.register("send_clarification_request", _execute_send_clarification_request)


async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
    """Execute approved sandbox actions in dry-run mode."""

    return await action_registry.execute(action)


@agent.tool_plain
async def get_department_context(department_id: str) -> dict[str, Any]:
    """Load the department file: cost center, approval chain, and memory."""

    return await tools.get_department_context(department_id)


@agent.tool_plain
async def lookup_vendor(vendor_name: str = "", vendor_id: str = "") -> dict[str, Any]:
    """Look up a vendor in the vendor file by name or id."""

    return await tools.lookup_vendor(vendor_name, vendor_id)


@agent.tool_plain
async def get_purchase_history(vendor_name: str, department_id: str = "", limit: int = 5) -> list[dict[str, Any]]:
    """Return recent purchases for this vendor and optional department."""

    return await tools.get_purchase_history(vendor_name, department_id, limit)


@agent.tool_plain
async def update_vendor_memory(vendor_name: str, memory: str) -> dict[str, Any]:
    """Update the vendor notepad with concise learnings from this case."""

    return await tools.update_vendor_memory(vendor_name, memory)


@agent.tool_plain
async def send_clarification_request(recipient: str, subject: str, message: str) -> dict[str, Any]:
    """Create a pending clarification-request action."""

    return await tools.send_clarification_request(recipient, subject, message)


@agent.tool_plain
async def create_approval_record(request_id: str, decision: str, approver_note: str) -> dict[str, Any]:
    """Create a pending approval-record action."""

    return await tools.create_approval_record(request_id, decision, approver_note)


@agent.tool_plain
async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search public references for edge cases not covered by internal books."""

    return await tools.web_search(query, max_results)


def _build_policy_context(request_context: dict[str, Any]) -> str:
    org = str(request_context.get("organization") or "ExampleCo").strip()
    region = str(request_context.get("region") or "US").strip()
    currency = str(request_context.get("currency") or "USD").strip()
    collections = _ACTIVE_KNOWLEDGE_COLLECTIONS.get()
    auto_approve_limit = request_context.get("auto_approve_limit")
    auto_approve = f"Auto-approve limit: {auto_approve_limit} {currency}." if auto_approve_limit else "No auto-approve limit supplied."
    return (
        f"Organization: {org}.\n"
        f"Region: {region}.\n"
        f"Working currency: {currency}.\n"
        f"Active knowledge collections: {', '.join(collections)}.\n"
        f"{auto_approve}"
    )


def before_run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Prepare policy scoping, dynamic instructions, resume context, and MCP toolsets."""

    request_context = input_data.get("request_context")
    if not isinstance(request_context, dict):
        request_context = {}

    collections: tuple[str, ...] = DEFAULT_KNOWLEDGE_COLLECTIONS
    raw_collections = request_context.get("knowledge_collections")
    if isinstance(raw_collections, list):
        normalized = tuple(
            str(item).strip()
            for item in raw_collections
            if isinstance(item, str) and item.strip()
        )
        if normalized:
            collections = normalized
    _ACTIVE_KNOWLEDGE_COLLECTIONS.set(collections)

    policy_context = _build_policy_context(request_context)
    langfuse_prompt = get_prompt(
        "procurement-compliance-officer-system-prompt",
        Settings.from_env(),
        policy_context=policy_context,
    )
    instructions = langfuse_prompt or SYSTEM_PROMPT.format(policy_context=policy_context)
    if input_data.get("message_history"):
        instructions += (
            "\n\nYou are resuming an existing procurement review. Use the stored "
            "conversation context and only update the parts affected by the new answer."
        )

    input_data["_instructions"] = instructions
    input_data["_toolsets"] = _create_mcp_toolsets()
    return input_data


def _purchase_request(input_data: dict[str, Any]) -> dict[str, Any]:
    purchase_request = input_data.get("purchase_request")
    if isinstance(purchase_request, dict):
        return purchase_request
    text = str(input_data.get("text") or "")
    return {"request_id": "REQ-MOCK", "business_justification": text}


def mock_result(input_data: dict[str, Any]) -> dict[str, Any]:
    """Schema-valid development response when no LLM key is configured."""

    request = _purchase_request(input_data)
    request_id = str(request.get("request_id") or "REQ-MOCK")
    requester_email = str(request.get("requester_email") or "requester@example.com")
    department_id = str(request.get("department_id") or "")
    vendor_name = str(request.get("vendor_name") or "")
    category = str(request.get("category") or "")
    amount = request.get("amount")
    business_justification = str(request.get("business_justification") or "")
    handles_sensitive_data = bool(request.get("handles_sensitive_data", False))
    sole_source_requested = bool(request.get("sole_source_requested", False))

    extracted = {
        "request_id": request_id,
        "requester_email": requester_email,
        "department_id": department_id,
        "vendor_name": vendor_name,
        "category": category,
        "amount": amount if isinstance(amount, (int, float)) else None,
        "currency": str(request.get("currency") or "USD"),
        "business_justification": business_justification,
        "purchase_type": str(request.get("purchase_type") or "unknown"),
        "contract_reference": str(request.get("contract_reference") or ""),
        "handles_sensitive_data": handles_sensitive_data,
        "sole_source_requested": sole_source_requested,
    }

    lowered_vendor = vendor_name.lower()
    if "northstar" in lowered_vendor or "blocked" in lowered_vendor:
        return {
            "status": "rejected",
            "extracted_fields": extracted,
            "vendor_risk": "blocked",
            "policy_checks": [
                {
                    "name": "Vendor sanctions screen",
                    "status": "failed",
                    "evidence": "Mock vendor-risk fixture marks this vendor as blocked.",
                    "source": "procurement-vendor-risk",
                }
            ],
            "required_approvals": [],
            "approval": None,
            "clarification": None,
            "rejection_reason": "Vendor is blocked by the vendor-risk policy fixture.",
            "missing_fields": [],
            "confidence": 0.9,
            "reasoning": "Mock mode identified a blocked vendor pattern.",
            "review_steps": ["Extract request", "Check vendor risk", "Reject prohibited vendor"],
            "pending_actions": [],
            "needs_review": False,
        }

    missing_fields = [
        field
        for field, value in {
            "department_id": department_id,
            "vendor_name": vendor_name,
            "category": category,
            "amount": amount,
            "business_justification": business_justification,
        }.items()
        if value in ("", None)
    ]
    if sole_source_requested and not request.get("sole_source_rationale"):
        missing_fields.append("sole_source_rationale")
    if handles_sensitive_data and not request.get("security_review_id"):
        missing_fields.append("security_review_id")

    if missing_fields:
        clarification = {
            "recipient": requester_email,
            "subject": f"Clarification needed for {request_id}",
            "message": "Please provide the missing procurement details: " + ", ".join(missing_fields),
            "missing_fields": missing_fields,
        }
        return {
            "status": "needs_clarification",
            "extracted_fields": extracted,
            "vendor_risk": "unknown",
            "policy_checks": [],
            "required_approvals": [],
            "approval": None,
            "clarification": clarification,
            "rejection_reason": None,
            "missing_fields": missing_fields,
            "confidence": 0.65,
            "reasoning": "Mock mode found missing request fields that a human must supply.",
            "review_steps": ["Extract request", "Identify missing fields", "Draft clarification"],
            "pending_actions": [
                {
                    "action": "send_clarification_request",
                    "params": {
                        "recipient": requester_email,
                        "subject": clarification["subject"],
                        "message": clarification["message"],
                    },
                    "description": f"Send clarification request for {request_id}",
                }
            ],
            "needs_review": False,
        }

    approval_level = "department_head" if float(amount) < 25_000 else "department_head_and_finance"
    approver_note = f"Approve {request_id} for {vendor_name}; policy checks pass in mock mode."
    return {
        "status": "approved",
        "extracted_fields": extracted,
        "vendor_risk": "low",
        "policy_checks": [
            {
                "name": "Request completeness",
                "status": "passed",
                "evidence": "Required mock fields are present.",
                "source": "mock_result",
            },
            {
                "name": "Approval threshold",
                "status": "passed",
                "evidence": f"Required approval level is {approval_level}.",
                "source": "procurement-policy-core",
            },
        ],
        "required_approvals": [approval_level],
        "approval": {
            "request_id": request_id,
            "decision": "approve",
            "approval_level": approval_level,
            "conditions": [],
            "approver_note": approver_note,
        },
        "clarification": None,
        "rejection_reason": None,
        "missing_fields": [],
        "confidence": 0.88,
        "reasoning": "Mock mode found a complete low-risk request.",
        "review_steps": ["Extract request", "Check completeness", "Assign approval level", "Prepare approval action"],
        "pending_actions": [
            {
                "action": "create_approval_record",
                "params": {
                    "request_id": request_id,
                    "decision": "approve",
                    "approver_note": approver_note,
                },
                "description": f"Create approval record for {request_id}",
            }
        ],
        "needs_review": False,
    }


async def after_run(input_data: dict[str, Any], output: dict[str, Any]) -> None:
    """Persist demo job output and mark low-confidence approvals for review."""

    if output.get("status") == "approved" and float(output.get("confidence", 0.0)) < 0.85:
        output["needs_review"] = True

    job_id = input_data.get("job_id")
    if job_id:
        await tools.record_case_result(str(job_id), {k: v for k, v in output.items() if k != "_message_history"})
