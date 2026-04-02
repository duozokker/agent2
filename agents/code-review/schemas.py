"""Output schemas for the code review agent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewFinding(BaseModel):
    """A single finding from the code review."""

    severity: Literal["info", "warning", "error", "critical"] = Field(
        description="How serious this finding is"
    )
    category: Literal[
        "bug", "security", "performance", "style", "maintainability", "testing",
    ] = Field(description="Type of issue found")
    line_reference: str = Field(description="Approximate location in the code (e.g. 'line 42' or 'function process_data')")
    description: str = Field(description="What the issue is")
    suggestion: str = Field(description="How to fix it")


class CodeReviewResult(BaseModel):
    """Structured code review output."""

    summary: str = Field(description="One-paragraph overall assessment")
    quality_score: float = Field(ge=0.0, le=10.0, description="Overall code quality (0-10)")
    findings: list[ReviewFinding] = Field(description="Specific issues found")
    strengths: list[str] = Field(description="What the code does well")
    estimated_review_time_minutes: int = Field(ge=0, description="How long a human review would take")
    approve: bool = Field(description="Whether this code is ready to merge")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the review")
