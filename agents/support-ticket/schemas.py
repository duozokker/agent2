"""Output schemas for the support ticket agent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """A single action to resolve the ticket."""

    description: str = Field(description="What needs to be done")
    assignee: Literal["support", "engineering", "billing", "management"] = Field(
        description="Team that should handle this"
    )
    priority: Literal["low", "medium", "high"] = Field(description="Priority of this action")


class TicketAnalysis(BaseModel):
    """Structured analysis of a customer support ticket."""

    summary: str = Field(description="One-sentence summary of the issue")
    category: Literal[
        "bug_report", "feature_request", "billing", "account_access",
        "how_to", "complaint", "other",
    ] = Field(description="Ticket category")
    urgency: Literal["low", "medium", "high", "critical"] = Field(
        description="How urgently this needs attention"
    )
    sentiment: Literal["positive", "neutral", "frustrated", "angry"] = Field(
        description="Customer sentiment"
    )
    action_items: list[ActionItem] = Field(description="Recommended next steps")
    suggested_response: str = Field(
        description="Draft reply to the customer (professional, empathetic)"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the analysis")
