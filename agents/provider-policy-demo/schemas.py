"""Schemas for the provider policy demo agent."""

from pydantic import BaseModel, Field


class ProviderPolicyDemoResult(BaseModel):
    status: str = Field(description="Result status")
    provider_order: list[str] = Field(default_factory=list)
    allow_fallbacks: bool = Field(default=True)
    confidence: float = Field(ge=0.0, le=1.0)
