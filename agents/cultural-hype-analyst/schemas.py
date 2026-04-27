"""Schemas for the cultural hype analyst agent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PendingAction(BaseModel):
    """An action the host may execute after human approval."""

    action: Literal["paper_trade"]
    params: dict = Field(default_factory=dict)
    description: str = ""


class SocialSignal(BaseModel):
    """A social signal observed in public communities."""

    source: str
    entity: str
    signal: Literal["positive", "negative", "mixed", "unclear"]
    evidence: str
    engagement: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)


class HypeRanking(BaseModel):
    """A ranked cultural entity such as an artist, contestant, movie, or album."""

    entity: str
    rank: int = Field(ge=1)
    why_it_matters: str
    momentum: Literal["rising", "stable", "falling", "unclear"]
    estimated_public_support: Literal["high", "medium", "low", "unclear"]
    evidence: list[str] = Field(default_factory=list)


class MarketCandidate(BaseModel):
    """A Polymarket market that may express the social thesis."""

    slug: str
    question: str
    yes_price: float | None = Field(default=None, ge=0.0, le=1.0)
    no_price: float | None = Field(default=None, ge=0.0, le=1.0)
    volume: float = Field(default=0.0, ge=0.0)
    liquidity: float = Field(default=0.0, ge=0.0)
    fit_reason: str
    resolution_risk: str


class PaperTradeSuggestion(BaseModel):
    """A zero-risk paper trade suggestion."""

    market_slug: str
    outcome: str
    amount_usd: float = Field(gt=0)
    thesis: str
    invalidation: str


class CulturalHypeResult(BaseModel):
    """Structured output for cultural and fan-driven markets."""

    status: Literal["opportunity_found", "needs_more_research", "no_trade"]
    topic: str
    summary: str
    hype_rankings: list[HypeRanking] = Field(default_factory=list)
    social_signals: list[SocialSignal] = Field(default_factory=list)
    matched_markets: list[MarketCandidate] = Field(default_factory=list)
    best_candidate: MarketCandidate | None = None
    paper_trade: PaperTradeSuggestion | None = None
    missing_research: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    review_steps: list[str] = Field(default_factory=list)
    pending_actions: list[PendingAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_consistency(self) -> "CulturalHypeResult":
        if self.status == "opportunity_found":
            if self.best_candidate is None:
                raise ValueError("best_candidate is required when status is opportunity_found")
            if self.paper_trade is None:
                raise ValueError("paper_trade is required when status is opportunity_found")
        if self.status == "no_trade" and self.paper_trade is not None:
            raise ValueError("paper_trade must be empty when status is no_trade")
        return self
