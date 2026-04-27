"""Tools for the procurement compliance officer flagship example.

The fixtures are intentionally small and local. Product teams should replace
these functions with their own ERP, vendor master, policy, and ticketing APIs.
Tools return errors as data so the agent can decide whether to continue, ask,
or reject.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


_DEPARTMENTS: dict[str, dict[str, Any]] = {
    "engineering": {
        "department_id": "engineering",
        "cost_center": "ENG-100",
        "manager": "Avery Chen",
        "approval_chain": ["department_head", "finance"],
        "memory": "Engineering often buys developer tooling. Security review is required for cloud software that processes source code or employee data.",
    },
    "marketing": {
        "department_id": "marketing",
        "cost_center": "MKT-200",
        "manager": "Riley Patel",
        "approval_chain": ["department_head", "finance"],
        "memory": "Marketing event spend must identify audience, gift value, and whether attendee personal data is collected.",
    },
}

_VENDORS: dict[str, dict[str, Any]] = {
    "acme hardware": {
        "vendor_id": "ven_acme_hardware",
        "vendor_name": "Acme Hardware",
        "risk_level": "low",
        "status": "approved",
        "memory": "Preferred vendor for laptops, docks, and standard peripherals.",
    },
    "collabcloud": {
        "vendor_id": "ven_collabcloud",
        "vendor_name": "CollabCloud",
        "risk_level": "medium",
        "status": "approved_with_conditions",
        "memory": "Cloud collaboration platform. Requires security review and DPA when user files or employee data are processed.",
    },
    "northstar intermediaries": {
        "vendor_id": "ven_northstar",
        "vendor_name": "Northstar Intermediaries",
        "risk_level": "blocked",
        "status": "blocked",
        "memory": "Blocked in example vendor-risk book due to sanctions-screening match.",
    },
}

_PURCHASE_HISTORY: list[dict[str, Any]] = [
    {
        "request_id": "REQ-2026-0101",
        "department_id": "engineering",
        "vendor_name": "Acme Hardware",
        "amount": 4200.0,
        "category": "hardware",
        "decision": "approved",
    },
    {
        "request_id": "REQ-2026-0118",
        "department_id": "engineering",
        "vendor_name": "CollabCloud",
        "amount": 18000.0,
        "category": "software",
        "decision": "approved_with_security_review",
    },
]

_CASE_RESULTS: dict[str, dict[str, Any]] = {}


def _normalize(value: str) -> str:
    return value.strip().lower()


async def get_department_context(department_id: str) -> dict[str, Any]:
    """Load the department file: cost center, approval chain, and memory."""

    department = _DEPARTMENTS.get(_normalize(department_id))
    if not department:
        return {
            "found": False,
            "department_id": department_id,
            "error": "Unknown department. Ask the requester to confirm the department or cost center.",
        }
    return {"found": True, **department}


async def lookup_vendor(vendor_name: str = "", vendor_id: str = "") -> dict[str, Any]:
    """Look up a vendor in the vendor file by name or id."""

    normalized = _normalize(vendor_name)
    for vendor in _VENDORS.values():
        if vendor_id and vendor.get("vendor_id") == vendor_id:
            return {"found": True, **vendor}
        if normalized and normalized in _normalize(str(vendor.get("vendor_name", ""))):
            return {"found": True, **vendor}
    return {
        "found": False,
        "vendor_name": vendor_name,
        "risk_level": "unknown",
        "status": "new_vendor",
        "memory": "",
    }


async def get_purchase_history(vendor_name: str, department_id: str = "", limit: int = 5) -> list[dict[str, Any]]:
    """Return recent purchases for this vendor and optional department."""

    vendor_key = _normalize(vendor_name)
    department_key = _normalize(department_id)
    results: list[dict[str, Any]] = []
    for purchase in _PURCHASE_HISTORY:
        if vendor_key and vendor_key not in _normalize(str(purchase.get("vendor_name", ""))):
            continue
        if department_key and department_key != _normalize(str(purchase.get("department_id", ""))):
            continue
        results.append(purchase)
        if len(results) >= limit:
            break
    return results


async def update_vendor_memory(vendor_name: str, memory: str) -> dict[str, Any]:
    """Update the local vendor memory with learnings from this case."""

    if len(memory) > 10_000:
        return {"success": False, "error": "Memory too long. Summarize to fewer than 10,000 characters."}
    normalized = _normalize(vendor_name)
    if not normalized:
        return {"success": False, "error": "vendor_name is required"}
    vendor = _VENDORS.setdefault(
        normalized,
        {
            "vendor_id": f"ven_{normalized.replace(' ', '_')}",
            "vendor_name": vendor_name,
            "risk_level": "unknown",
            "status": "new_vendor",
            "memory": "",
        },
    )
    vendor["memory"] = memory
    vendor["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"success": True, "vendor_name": vendor["vendor_name"]}


async def send_clarification_request(recipient: str, subject: str, message: str) -> dict[str, Any]:
    """SANDBOX: propose a clarification message for human approval."""

    return {
        "pending": True,
        "action": "send_clarification_request",
        "params": {
            "recipient": recipient,
            "subject": subject,
            "message": message,
        },
        "description": f"Send clarification request to {recipient}: {subject}",
    }


async def create_approval_record(request_id: str, decision: str, approver_note: str) -> dict[str, Any]:
    """SANDBOX: propose writing the approval package to the procurement system."""

    return {
        "pending": True,
        "action": "create_approval_record",
        "params": {
            "request_id": request_id,
            "decision": decision,
            "approver_note": approver_note,
        },
        "description": f"Create procurement approval record for {request_id}",
    }


async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Return public-reference placeholders for edge cases outside the books."""

    return {
        "source": "example-static-web-search",
        "query": query,
        "results": [
            {
                "title": "Example public procurement guidance",
                "url": "https://example.com/procurement-guidance",
                "content": "Use public sources only as a fallback when internal books do not answer the question.",
            }
        ][:max_results],
    }


async def record_case_result(job_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Persist the final result in a local in-memory case store for demos/tests."""

    _CASE_RESULTS[job_id] = {
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    return {"success": True, "job_id": job_id}
