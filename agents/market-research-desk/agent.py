"""Market research desk agent."""
from __future__ import annotations

from typing import Any

from shared.action_executor import ActionRegistry
from shared.runtime import create_agent

from . import tools
from .schemas import DeskResult


SYSTEM_PROMPT = """\
You are the lead analyst of a small prediction-market research desk.

You coordinate four mental roles, but you produce one structured answer:

1. Social Scout — reads public communities and finds unusual attention,
   consensus, disagreement, narrative shifts, and sentiment anomalies.
2. Market Matcher — finds Polymarket markets that express the topic cleanly.
3. Thesis Analyst — writes the bull case, bear case, resolution risks, and what
   would change the view.
4. Paper Trader — proposes only zero-risk paper trades or watchlist items.

This is not a rules engine. Work like a human research team. Prefer a clear
thesis with uncertainty over fake precision. Reject trades when the social
signal does not map to the market resolution.

## Your Workspace

- scan_communities() searches public Reddit communities.
- fetch_reddit_thread() reads a promising thread.
- find_polymarket_markets() searches active markets.
- get_orderbook_snapshot() checks public CLOB depth for token ids.
- propose_paper_trade() creates a pending paper trade action only.
- create_watchlist_item() creates a pending watchlist action only.

## How You Think

Start with the topic and communities. Ask:
- What is the real-world event?
- Which people or groups are talking?
- Is the signal expected, or is someone breaking from their usual stance?
- Which markets map directly to this topic?
- Does the orderbook price leave room for edge?
- What is the cleanest paper-trade or watchlist action?

## Three Outcomes

- paper_trade_ready: the desk found a concrete market, a thesis, and a paper
  trade plan.
- watchlist_only: evidence is interesting, but trade timing or market fit is
  not strong enough.
- reject: signal is too weak, too noisy, stale, or not tradable.
"""

output_type = DeskResult


agent = create_agent(
    name="market-research-desk",
    output_type=DeskResult,
    instructions=SYSTEM_PROMPT,
    toolsets=[],
)

action_registry = ActionRegistry()


async def _execute_paper_trade(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "executed": True,
        "dry_run": True,
        "message": "Paper trade accepted by approval workflow. No real order was placed.",
        "params": action.get("params", {}),
    }


async def _execute_watchlist_item(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "executed": True,
        "dry_run": True,
        "message": "Watchlist item accepted by approval workflow. Persist it in the host product if desired.",
        "params": action.get("params", {}),
    }


action_registry.register("paper_trade", _execute_paper_trade)
action_registry.register("create_watchlist_item", _execute_watchlist_item)


async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
    """Execute approved actions in dry-run mode only."""
    return await action_registry.execute(action)


@agent.tool_plain
def scan_communities(subreddits: str, query: str, limit_per_subreddit: int = 5) -> dict:
    """Search several public Reddit communities for a topic."""
    return tools.scan_communities(subreddits, query, limit_per_subreddit)


@agent.tool_plain
def fetch_reddit_thread(url_or_id: str, limit: int = 25) -> dict:
    """Fetch a public Reddit thread by permalink URL or post id."""
    return tools.fetch_reddit_thread(url_or_id, limit)


@agent.tool_plain
def find_polymarket_markets(query: str, limit: int = 10) -> dict:
    """Find active Polymarket markets for a research topic."""
    return tools.find_polymarket_markets(query, limit)


@agent.tool_plain
def get_orderbook_snapshot(token_id: str) -> dict:
    """Get a compact public CLOB orderbook snapshot for one token id."""
    return tools.get_orderbook_snapshot(token_id)


@agent.tool_plain
def propose_paper_trade(market_slug: str, outcome: str, amount_usd: float, thesis: str) -> dict:
    """Create a pending zero-risk paper trade action."""
    return tools.propose_paper_trade(market_slug, outcome, amount_usd, thesis)


@agent.tool_plain
def create_watchlist_item(topic: str, market_slug: str, reason: str) -> dict:
    """Create a pending watchlist action."""
    return tools.create_watchlist_item(topic, market_slug, reason)


def before_run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Inject a continuation hint when resuming a research thread."""
    if input_data.get("message_history"):
        input_data["_instructions"] = SYSTEM_PROMPT + (
            "\n\nYou are resuming an existing research-desk thread. "
            "Use the prior scout/matcher/thesis context and update only what changed."
        )
    return input_data


def mock_result(input_data: dict[str, Any]) -> dict[str, Any]:
    """Schema-valid development response when no LLM key is configured."""
    topic = str(input_data.get("topic") or input_data.get("query") or "Trump Iran")
    return {
        "status": "watchlist_only",
        "topic": topic,
        "executive_summary": "Mock research desk result: collect social evidence, match markets, then propose a paper trade only if the thesis is clean.",
        "social_scout": {
            "topic": topic,
            "communities_checked": [],
            "key_observations": [],
            "unusual_consensus": "Not assessed in mock mode.",
            "signal_strength": "none",
        },
        "market_matches": [],
        "thesis_review": {
            "thesis": "Mock mode is active.",
            "bull_case": [],
            "bear_case": ["No live LLM analysis was performed."],
            "resolution_risks": [],
            "what_would_change_my_mind": ["Run with an LLM key and live social/market tool calls."],
            "confidence": 0.25,
        },
        "paper_trade_plan": None,
        "next_subtasks": ["Scan communities", "Find matching markets", "Inspect orderbook", "Decide paper trade"],
        "confidence": 0.25,
        "pending_actions": [],
    }
