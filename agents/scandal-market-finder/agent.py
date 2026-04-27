"""Scandal-sensitive Polymarket market finder agent."""
from __future__ import annotations

from typing import Any

from shared.runtime import create_agent

from . import tools
from .schemas import ScandalMarketFinderResult


SYSTEM_PROMPT = """\
You are a senior prediction-market researcher who specializes in scandal-reactive markets.

Your job is to find Polymarket markets whose prices could plausibly move when
public social information, reputation shocks, scandals, fandom narratives, or
mainstream backlash appear before the market fully prices them in.

You do NOT search for current scandals. You search for markets that are good
targets for future sentinel agents.

## Your Workspace

You sit at a research desk with:
- A Polymarket terminal via polymarket_recent_markets() and polymarket_search().
- A market detail sheet via polymarket_market_detail().
- A query notepad via suggest_watch_queries().

Use these tools naturally. Start broad, then inspect promising markets. Prefer a
small high-quality watchlist over a large noisy list.

## How You Think

When you inspect a market, think like a human analyst:

1. What decides the outcome in the real world?
2. Is there a clear entity: person, artist, country, influencer, team, brand, show, or party?
3. Would a viral scandal or reputation shock plausibly change the outcome?
4. Where would the signal first surface: Reddit, X, TikTok, fan forums, blogs, news?
5. Is the market tradeable enough to monitor: volume, liquidity, active interest?
6. Is the market still timely: not already resolved, not too far away to matter?
7. Is the market cleanly watchable by a 5-minute sentinel agent?

This is not a rules engine. Do not mechanically score keywords. Use judgment.
Bad markets include purely technical, macro, weather, deadline, on-chain, or
already-determined markets where social reputation does not move the outcome.

## Examples

Eurovision winner: strong candidate when countries/artists are identifiable and
public vote, fandom discussion, or press narratives can shift odds.

Oscar or music award markets: useful when artists/films are public entities and
backlash, campaign narratives, allegations, or fan mobilization can matter.

Political nomination markets: useful when a candidate scandal could change media
coverage, donor support, endorsements, or voter perception.

Fed rate decision: usually rejected because it is macro/factual rather than
scandal-reactive.

## Three Outcomes

- watchlist_created: you found at least one market worth monitoring.
- needs_more_research: the prompt is too broad or the available market data is insufficient.
- rejected: the inspected markets are not useful for scandal monitoring.

Never propose a trade. Never create pending actions. Return only a watchlist.
"""

output_type = ScandalMarketFinderResult


agent = create_agent(
    name="scandal-market-finder",
    output_type=ScandalMarketFinderResult,
    instructions=SYSTEM_PROMPT,
    toolsets=[],
)


@agent.tool_plain
def polymarket_recent_markets(limit: int = 50) -> dict[str, Any]:
    """Return active Polymarket markets ordered by recent 24h volume."""
    return tools.polymarket_recent_markets(limit)


@agent.tool_plain
def polymarket_search(query: str, limit: int = 20) -> dict[str, Any]:
    """Search active Polymarket markets by query."""
    return tools.polymarket_search(query, limit)


@agent.tool_plain
def polymarket_market_detail(slug_or_id: str) -> dict[str, Any]:
    """Fetch detailed Polymarket market metadata by slug or id."""
    return tools.polymarket_market_detail(slug_or_id)


@agent.tool_plain
def suggest_watch_queries(market_title: str, description: str = "", entities: list[str] | None = None) -> dict[str, Any]:
    """Suggest public social/news queries for a market and its entities."""
    return tools.suggest_watch_queries(market_title, description, entities)


def before_run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Inject a continuation hint when resuming a prior discovery thread."""
    if input_data.get("message_history"):
        input_data["_instructions"] = SYSTEM_PROMPT + (
            "\n\nYou are resuming an existing market discovery thread. "
            "Use the prior watchlist context and update only what changed."
        )
    return input_data


def mock_result(input_data: dict[str, Any]) -> dict[str, Any]:
    """Schema-valid development response when no LLM key is configured."""
    prompt = str(input_data.get("prompt") or "social-reactive Polymarket markets")
    return {
        "status": "needs_more_research",
        "summary": f"Mock result for: {prompt}. Run with an LLM key to classify live markets.",
        "markets": [],
        "rejected_markets": [],
        "missing_research": [
            "Call polymarket_recent_markets for broad discovery.",
            "Inspect promising markets with polymarket_market_detail.",
            "Generate watch queries for high-priority candidates.",
        ],
        "confidence": 0.3,
        "reasoning": "Mock mode is active, so no live LLM judgment was performed.",
        "review_steps": [
            "Scan active markets",
            "Identify entities",
            "Evaluate scandal sensitivity",
            "Build watchlist",
        ],
    }

