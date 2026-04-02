"""Schemas for the approval demo agent."""

from pydantic import BaseModel, Field


class PendingAction(BaseModel):
    action: str
    params: dict = Field(default_factory=dict)
    description: str = ""


class ApprovalDemoResult(BaseModel):
    status: str = Field(description="Result status")
    message: str = Field(description="Summary of the run")
    confidence: float = Field(ge=0.0, le=1.0)
    pending_actions: list[PendingAction] = Field(default_factory=list)
