"""Schemas for the resume demo agent."""

from pydantic import BaseModel, Field


class ResumeDemoResult(BaseModel):
    status: str = Field(description="fresh or resumed")
    reply: str = Field(description="Agent reply")
    turns: int = Field(ge=0, description="Conversation turns seen")
    confidence: float = Field(ge=0.0, le=1.0)
