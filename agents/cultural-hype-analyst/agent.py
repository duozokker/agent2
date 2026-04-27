"""Cultural hype analyst agent."""
from __future__ import annotations

from typing import Any

from shared.action_executor import ActionRegistry
from shared.runtime import create_agent

from . import tools
from .schemas import CulturalHypeResult


SYSTEM_PROMPT = """\
You are a senior cultural prediction-market analyst.

You do not use rigid trading rules. You work like a human analyst who studies
public attention, fandom intensity, backlash, momentum, and market structure.
Your job is to find culture-driven Polymarket opportunities, especially in
Eurovision, music releases, awards, movies, creators, games, and fandom events.

## Your Workspace

You sit at your desk with:
- Reddit communities via reddit_search() and reddit_posts().
- Polymarket market search via polymarket_search() and polymarket_market_detail().
- A paper-trade notepad via propose_paper_trade(). It only proposes a pending
  action; it never uses real money and never executes automatically.

Use tools naturally, like a human analyst. If the provided input already contains
data, use it. If it only contains a topic, gather a small amount of evidence first.

## How You Think

When a cultural topic lands on your desk, think through it:
1. What is the event and what actually decides the outcome?
2. Which entities matter: artists, contestants, songs, albums, films, countries?
3. What are public communities saying, and is that enthusiasm broad or niche?
4. Is engagement real discussion or just noise, memes, brigading, or controversy?
5. Which Polymarket markets express the thesis cleanly?
6. Is the resolution wording compatible with the social signal?
7. What would make the thesis wrong?
8. Should we paper-trade, watch, or pass?

## Important Judgment

Do not convert sentiment directly into probability. Social hype is only useful
when it maps to the actual resolution mechanism. For jury-heavy events, be more
cautious. For fan votes, album sales, box office, and public attention markets,
social momentum can matter more.

## Three Outcomes

- opportunity_found: there is a concrete matched market and a zero-risk paper
  trade suggestion.
- needs_more_research: the topic is interesting but evidence or market fit is
  insufficient.
- no_trade: the signal is weak, noisy, stale, or not connected to a market.
"""

output_type = CulturalHypeResult


agent = create_agent(
    name="cultural-hype-analyst",
    output_type=CulturalHypeResult,
    instructions=SYSTEM_PROMPT,
    toolsets=[],
)

action_registry = ActionRegistry()


async def _execute_paper_trade(action: dict[str, Any]) -> dict[str, Any]:
    params = action.get("params", {})
    return {
        "executed": True,
        "dry_run": True,
        "message": "Paper trade accepted by approval workflow. No real order was placed.",
        "params": params,
    }


action_registry.register("paper_trade", _execute_paper_trade)


async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
    """Execute approved actions in dry-run mode only."""
    return await action_registry.execute(action)


@agent.tool_plain
def reddit_search(subreddit: str, query: str, limit: int = 10, sort: str = "new", time: str = "week") -> dict:
    """Search public Reddit posts in one subreddit or all of Reddit."""
    return tools.reddit_search(subreddit, query, limit, sort, time)


@agent.tool_plain
def reddit_posts(subreddit: str, sort: str = "hot", limit: int = 10, time: str = "week") -> dict:
    """List public Reddit posts for a subreddit."""
    return tools.reddit_posts(subreddit, sort, limit, time)


@agent.tool_plain
def polymarket_search(query: str, limit: int = 10) -> dict:
    """Search active Polymarket markets for culture-related candidates."""
    return tools.polymarket_search(query, limit)


@agent.tool_plain
def polymarket_market_detail(slug_or_id: str) -> dict:
    """Fetch detailed Polymarket market metadata by slug or id."""
    return tools.polymarket_market_detail(slug_or_id)


@agent.tool_plain
def propose_paper_trade(market_slug: str, outcome: str, amount_usd: float, thesis: str) -> dict:
    """Create a pending zero-risk paper trade action."""
    return tools.propose_paper_trade(market_slug, outcome, amount_usd, thesis)


def before_run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Inject a continuation hint when the host resumes a prior research thread."""
    if input_data.get("message_history"):
        input_data["_instructions"] = SYSTEM_PROMPT + (
            "\n\nYou are resuming an existing cultural market analysis. "
            "Use the prior context, incorporate the user's new information, and avoid restarting from scratch."
        )
    return input_data


def mock_result(input_data: dict[str, Any]) -> dict[str, Any]:
    """Schema-valid development response when no LLM key is configured."""
    topic = str(input_data.get("topic") or input_data.get("query") or "Eurovision hype")
    return {
        "status": "needs_more_research",
        "topic": topic,
        "summary": "Mock analysis: collect Reddit evidence, rank cultural entities, then match them to Polymarket markets.",
        "hype_rankings": [],
        "social_signals": [],
        "matched_markets": [],
        "best_candidate": None,
        "paper_trade": None,
        "missing_research": ["Run reddit_search for relevant communities.", "Run polymarket_search for matching markets."],
        "confidence": 0.35,
        "reasoning": "Mock mode is active, so no LLM analysis was performed.",
        "review_steps": ["Identify event", "Collect social evidence", "Match market", "Decide paper trade"],
        "pending_actions": [],
    }
