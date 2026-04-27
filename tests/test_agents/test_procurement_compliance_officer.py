"""Tests for the procurement compliance officer flagship example."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_PATH = ROOT / "agents" / "procurement-compliance-officer" / "schemas.py"


def _load_schemas():
    spec = importlib.util.spec_from_file_location("procurement_compliance_schemas", SCHEMAS_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_approved_result_requires_approval_record() -> None:
    schemas = _load_schemas()

    with pytest.raises(ValidationError):
        schemas.ProcurementComplianceResult(
            status="approved",
            extracted_fields=schemas.ExtractedPurchaseFields(
                request_id="REQ-1",
                requester_email="requester@example.com",
                department_id="engineering",
                vendor_name="Acme Hardware",
                category="hardware",
                amount=4200,
                business_justification="Replacement laptop",
            ),
            vendor_risk="low",
            approval=None,
            confidence=0.9,
            reasoning="Approved without an approval record should fail.",
        )


def test_clarification_result_requires_missing_fields() -> None:
    schemas = _load_schemas()

    with pytest.raises(ValidationError):
        schemas.ProcurementComplianceResult(
            status="needs_clarification",
            extracted_fields=schemas.ExtractedPurchaseFields(request_id="REQ-2"),
            vendor_risk="unknown",
            clarification=schemas.ClarificationRequest(
                recipient="requester@example.com",
                subject="Need details",
                message="Please add details.",
                missing_fields=[],
            ),
            missing_fields=[],
            confidence=0.6,
            reasoning="Clarification without missing fields should fail.",
        )


def test_rejected_result_rejects_approval_payload() -> None:
    schemas = _load_schemas()

    with pytest.raises(ValidationError):
        schemas.ProcurementComplianceResult(
            status="rejected",
            extracted_fields=schemas.ExtractedPurchaseFields(request_id="REQ-3"),
            vendor_risk="blocked",
            approval=schemas.ApprovalRecord(
                request_id="REQ-3",
                decision="approve",
                approval_level="department_head",
                approver_note="Should not exist.",
            ),
            rejection_reason="Blocked vendor.",
            confidence=0.95,
            reasoning="Rejected result must not carry an approval record.",
        )


def test_before_run_injects_dynamic_prompt_and_per_run_toolsets(monkeypatch) -> None:
    from shared.api import _load_source_agent_module

    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    module = _load_source_agent_module("procurement-compliance-officer")

    prepared = module.before_run(
        {
            "purchase_request": {"request_id": "REQ-4"},
            "request_context": {
                "organization": "ExampleCo",
                "region": "US",
                "knowledge_collections": ["procurement-policy-core"],
            },
        }
    )

    assert "Organization: ExampleCo." in prepared["_instructions"]
    assert "procurement-policy-core" in prepared["_instructions"]
    assert prepared["_toolsets"]


def test_mock_result_returns_approved_pending_action(monkeypatch) -> None:
    from shared.api import _load_source_agent_module

    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    module = _load_source_agent_module("procurement-compliance-officer")

    result = module.mock_result(
        {
            "purchase_request": {
                "request_id": "REQ-5",
                "requester_email": "requester@example.com",
                "department_id": "engineering",
                "vendor_name": "Acme Hardware",
                "category": "hardware",
                "amount": 4200,
                "business_justification": "Replacement laptop for developer onboarding.",
                "purchase_type": "replacement",
            }
        }
    )

    assert result["status"] == "approved"
    assert result["approval"]["request_id"] == "REQ-5"
    assert result["pending_actions"][0]["action"] == "create_approval_record"
