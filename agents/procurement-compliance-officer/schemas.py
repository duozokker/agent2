"""Structured output schemas for the procurement compliance officer agent."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


Status = Literal["approved", "needs_clarification", "rejected"]
RiskLevel = Literal["low", "medium", "high", "blocked", "unknown"]


class PendingAction(BaseModel):
    """A side effect that a host may execute after human approval."""

    action: Literal["create_approval_record", "send_clarification_request"]
    params: dict = Field(default_factory=dict)
    description: str = ""


class ClarificationRequest(BaseModel):
    """A precise request for missing procurement context."""

    recipient: str
    subject: str
    message: str
    missing_fields: list[str] = Field(default_factory=list)


class ExtractedPurchaseFields(BaseModel):
    """Normalized facts extracted from the purchase request."""

    request_id: str = ""
    requester_email: str = ""
    department_id: str = ""
    vendor_name: str = ""
    category: str = ""
    amount: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    business_justification: str = ""
    purchase_type: Literal["new", "renewal", "replacement", "unknown"] = "unknown"
    contract_reference: str = ""
    handles_sensitive_data: bool = False
    sole_source_requested: bool = False


class PolicyCheck(BaseModel):
    """One policy question the officer checked."""

    name: str
    status: Literal["passed", "needs_clarification", "failed", "not_applicable"]
    evidence: str
    source: str = ""


class ApprovalRecord(BaseModel):
    """The structured approval package for a compliant purchase."""

    request_id: str
    decision: Literal["approve"]
    approval_level: str
    conditions: list[str] = Field(default_factory=list)
    approver_note: str


class ProcurementComplianceResult(BaseModel):
    """Top-level result for one procurement compliance case."""

    status: Status
    extracted_fields: ExtractedPurchaseFields
    vendor_risk: RiskLevel
    policy_checks: list[PolicyCheck] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    approval: ApprovalRecord | None = None
    clarification: ClarificationRequest | None = None
    rejection_reason: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    review_steps: list[str] = Field(default_factory=list)
    pending_actions: list[PendingAction] = Field(default_factory=list)
    needs_review: bool = False

    @model_validator(mode="after")
    def _check_status_consistency(self) -> Self:
        if self.status == "approved":
            if self.approval is None:
                raise ValueError("approval is required when status is approved")
            if self.clarification is not None:
                raise ValueError("clarification must be empty when status is approved")
            if self.rejection_reason:
                raise ValueError("rejection_reason must be empty when status is approved")
            if self.missing_fields:
                raise ValueError("missing_fields must be empty when status is approved")

        if self.status == "needs_clarification":
            if self.clarification is None:
                raise ValueError("clarification is required when status is needs_clarification")
            if not self.missing_fields:
                raise ValueError("missing_fields are required when status is needs_clarification")
            if self.approval is not None:
                raise ValueError("approval must be empty when status is needs_clarification")
            if self.rejection_reason:
                raise ValueError("rejection_reason must be empty when status is needs_clarification")

        if self.status == "rejected":
            if not self.rejection_reason:
                raise ValueError("rejection_reason is required when status is rejected")
            if self.approval is not None:
                raise ValueError("approval must be empty when status is rejected")
            if self.clarification is not None:
                raise ValueError("clarification must be empty when status is rejected")

        return self
