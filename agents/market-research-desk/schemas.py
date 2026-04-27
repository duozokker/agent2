"""Schemas for the market research desk agent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PendingAction(BaseModel):
    """An action the host may execute after human approval."""

    action: Literal["paper_trade", "create_watchlist_item"]
    params: dict = Field(default_factory=dict)
    description: str = ""


class SocialScoutReport(BaseModel):
    """What the social scout found."""

    topic: str
    communities_checked: list[str] = Field(default_factory=list)
    key_observations: list[str] = Field(default_factory=list)
    unusual_consensus: str
    signal_strength: Literal["strong", "medium", "weak", "none"]


class MarketMatch(BaseModel):
    """A market found by the market matcher."""

    slug: str
    question: str
    yes_price: float | None = Field(default=None, ge=0.0, le=1.0)
    no_price: float | None = Field(default=None, ge=0.0, le=1.0)
    volume: float = Field(default=0.0, ge=0.0)
    liquidity: float = Field(default=0.0, ge=0.0)
    match_quality: Literal["high", "medium", "low"]
    fit_reason: str


class ThesisReview(BaseModel):
    """The thesis analyst's review."""

    thesis: str
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    resolution_risks: list[str] = Field(default_factory=list)
    what_would_change_my_mind: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class PaperTradePlan(BaseModel):
    """A zero-risk paper trade plan."""

    market_slug: str
    outcome: str
    amount_usd: float = Field(gt=0)
    max_loss_usd: float = Field(ge=0)
    reason: str
    review_after: str


class DeskResult(BaseModel):
    """Structured result from the mini research desk."""

    status: Literal["paper_trade_ready", "watchlist_only", "reject"]
    topic: str
    executive_summary: str
    social_scout: SocialScoutReport
    market_matches: list[MarketMatch] = Field(default_factory=list)
    thesis_review: ThesisReview
    paper_trade_plan: PaperTradePlan | None = None
    next_subtasks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    pending_actions: list[PendingAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_consistency(self) -> "DeskResult":
        if self.status == "paper_trade_ready" and self.paper_trade_plan is None:
            raise ValueError("paper_trade_plan is required when status is paper_trade_ready")
        if self.status == "reject" and self.paper_trade_plan is not None:
            raise ValueError("paper_trade_plan must be empty when status is reject")
        return self
