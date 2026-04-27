"""Output schemas for the scandal-market-finder agent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


SignalLevel = Literal["low", "medium", "high"]
Status = Literal["watchlist_created", "needs_more_research", "rejected"]


class WatchlistMarket(BaseModel):
    """A Polymarket market worth monitoring for future reputation shocks."""

    market_title: str
    market_slug: str = ""
    category: str = Field(default="unknown")
    entity_type: str = Field(default="unknown")
    entities: list[str] = Field(default_factory=list)
    why_scandal_reactive: str
    scandal_sensitivity: SignalLevel
    social_surface: SignalLevel
    tradeability: SignalLevel
    watch_priority: SignalLevel
    possible_catalysts: list[str] = Field(default_factory=list)
    watch_sources: list[str] = Field(default_factory=list)
    watch_queries: list[str] = Field(default_factory=list)
    next_agent_task: str = Field(
        default="Start market-sentinel for this market every 5 minutes."
    )


class RejectedMarket(BaseModel):
    """A market that was inspected but is not useful for scandal monitoring."""

    market_title: str
    market_slug: str = ""
    reason: str


class ScandalMarketFinderResult(BaseModel):
    """Top-level structured result for scandal-reactive market discovery."""

    status: Status
    summary: str
    markets: list[WatchlistMarket] = Field(default_factory=list)
    rejected_markets: list[RejectedMarket] = Field(default_factory=list)
    missing_research: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    review_steps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_status_consistency(self) -> "ScandalMarketFinderResult":
        if self.status == "watchlist_created" and not self.markets:
            raise ValueError("markets must be provided when status is watchlist_created")
        if self.status == "rejected" and not (self.rejected_markets or self.missing_research):
            raise ValueError("rejected status requires rejected_markets or missing_research")
        return self

