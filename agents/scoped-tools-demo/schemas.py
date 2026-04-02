"""Schemas for the scoped tools demo agent."""

from pydantic import BaseModel, Field


class ScopedToolsDemoResult(BaseModel):
    status: str = Field(description="Result status")
    active_collections: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
