"""Structured output schema for the interview evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceStrongAnswer(BaseModel):
    quote: str = Field(description="Short transcript quote that supports a positive signal")
    why_it_worked: str


class EvidenceWeakAnswer(BaseModel):
    quote: str = Field(description="Short transcript quote that shows a weakness")
    improvement: str


class Evidence(BaseModel):
    strong_answers: list[EvidenceStrongAnswer] = Field(default_factory=list)
    weak_answers: list[EvidenceWeakAnswer] = Field(default_factory=list)
    missed_opportunities: list[str] = Field(default_factory=list)


class ActionPlan(BaseModel):
    improvements: list[str] = Field(min_length=5, max_length=5)
    drill_questions: list[str] = Field(min_length=5, max_length=5)
    anki_cards: list[dict[str, str]] = Field(default_factory=list, max_length=10)


class InterviewEvaluatorResult(BaseModel):
    readiness_score: int = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    strongest_selling_points: list[str] = Field(min_length=1)
    scorecard: dict[str, int]
    evidence: Evidence
    action_plan: ActionPlan
    markdown: str

    @model_validator(mode="after")
    def _check_report_consistency(self) -> "InterviewEvaluatorResult":
        required = {
            "rollenfit",
            "motivation",
            "konkretheit",
            "schwaechen_umgang",
            "kommunikation",
            "domain_fit",
            "rueckfragenqualitaet",
        }
        missing = required.difference(self.scorecard)
        if missing:
            raise ValueError(f"scorecard missing keys: {sorted(missing)}")
        for key, value in self.scorecard.items():
            if value < 0 or value > 100:
                raise ValueError(f"scorecard value for {key} must be between 0 and 100")
        if self.risk_level == "low" and self.readiness_score < 70:
            raise ValueError("risk_level low requires readiness_score >= 70")
        if self.risk_level == "high" and self.readiness_score > 65:
            raise ValueError("risk_level high requires readiness_score <= 65")
        if not self.markdown.strip().startswith("#"):
            raise ValueError("markdown must be a report document with a heading")
        return self
