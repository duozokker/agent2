"""Read-only tools for the market research desk."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx


REDDIT_BASE = "https://www.reddit.com"
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"
USER_AGENT = os.environ.get("REDDIT_RO_USER_AGENT", "script:agent2-market-research-desk:v0.2.0")


def _client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20.0, follow_redirects=True)


def _parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _as_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def scan_communities(subreddits: str, query: str, limit_per_subreddit: int = 5) -> dict:
    """Search several public Reddit communities for a topic."""
    communities = [item.strip().strip("/").removeprefix("r/") for item in subreddits.split(",") if item.strip()]
    limit = max(1, min(limit_per_subreddit, 15))
    results = []
    with _client() as client:
        for community in communities:
            response = client.get(
                f"{REDDIT_BASE}/r/{community}/search.json",
                params={"q": query, "restrict_sr": "1", "limit": limit, "sort": "new", "t": "week"},
            )
            if response.status_code >= 400:
                results.append({"subreddit": community, "error": response.text[:200], "posts": []})
                continue
            data = response.json()
            posts = []
            for child in data.get("data", {}).get("children", []):
                item = child.get("data", {})
                posts.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "score": item.get("score", 0),
                    "num_comments": item.get("num_comments", 0),
                    "created_utc": item.get("created_utc", 0),
                    "permalink": f"{REDDIT_BASE}{item.get('permalink', '')}",
                    "selftext_snippet": (item.get("selftext") or "")[:500],
                })
            results.append({"subreddit": community, "posts": posts})
    return {"ok": True, "query": query, "communities": results}


def fetch_reddit_thread(url_or_id: str, limit: int = 25) -> dict:
    """Fetch a public Reddit thread by permalink URL or post id."""
    value = url_or_id.strip()
    if value.startswith("http"):
        url = value.rstrip("/") + ".json"
    else:
        url = f"{REDDIT_BASE}/comments/{value}.json"
    with _client() as client:
        response = client.get(url, params={"limit": max(1, min(limit, 50))})
        response.raise_for_status()
        data = response.json()
    post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {}) if data else {}
    comments = []
    if len(data) > 1:
        for child in data[1].get("data", {}).get("children", []):
            item = child.get("data", {})
            if item.get("body"):
                comments.append({
                    "author": item.get("author", ""),
                    "score": item.get("score", 0),
                    "body_snippet": item.get("body", "")[:700],
                    "permalink": f"{REDDIT_BASE}{item.get('permalink', '')}",
                })
    return {
        "ok": True,
        "post": {
            "title": post_data.get("title", ""),
            "score": post_data.get("score", 0),
            "num_comments": post_data.get("num_comments", 0),
            "permalink": f"{REDDIT_BASE}{post_data.get('permalink', '')}",
        },
        "comments": comments,
    }


def find_polymarket_markets(query: str, limit: int = 10) -> dict:
    """Find active Polymarket markets for a research topic."""
    limit = max(1, min(limit, 30))
    params = {
        "active": "true",
        "closed": "false",
        "archived": "false",
        "limit": 250,
        "order": "volume24hr",
        "ascending": "false",
    }
    with _client() as client:
        response = client.get(f"{GAMMA_BASE}/markets", params=params)
        response.raise_for_status()
        markets = response.json()

    terms = [term.lower() for term in query.split() if term.strip()]
    matches = []
    for market in markets:
        haystack = " ".join(str(market.get(key, "")) for key in ("question", "description", "slug")).lower()
        if terms and not all(term in haystack for term in terms):
            continue
        prices = [_as_float(item) for item in _parse_json_list(market.get("outcomePrices"))]
        matches.append({
            "id": market.get("id", ""),
            "slug": market.get("slug", ""),
            "question": market.get("question", ""),
            "description": (market.get("description") or "")[:1200],
            "yes_price": prices[0] if prices else None,
            "no_price": prices[1] if len(prices) > 1 else None,
            "volume": _as_float(market.get("volume") or market.get("volumeNum")) or 0.0,
            "volume24hr": _as_float(market.get("volume24hr")) or 0.0,
            "liquidity": _as_float(market.get("liquidity") or market.get("liquidityNum")) or 0.0,
            "end_date": market.get("endDate", ""),
            "clob_token_ids": _parse_json_list(market.get("clobTokenIds")),
        })
        if len(matches) >= limit:
            break
    return {"ok": True, "query": query, "markets": matches}


def get_orderbook_snapshot(token_id: str) -> dict:
    """Get a compact public CLOB orderbook snapshot for one token id."""
    with _client() as client:
        book_response = client.get(f"{CLOB_BASE}/book", params={"token_id": token_id})
        book_response.raise_for_status()
        midpoint_response = client.get(f"{CLOB_BASE}/midpoint", params={"token_id": token_id})
        midpoint = midpoint_response.json().get("mid") if midpoint_response.status_code < 400 else None
    book = book_response.json()
    bids = sorted(book.get("bids", []), key=lambda row: _as_float(row.get("price")) or -1, reverse=True)
    asks = sorted(book.get("asks", []), key=lambda row: _as_float(row.get("price")) or 2)
    return {
        "ok": True,
        "midpoint": _as_float(midpoint),
        "best_bid": bids[0] if bids else None,
        "best_ask": asks[0] if asks else None,
        "top_bids": bids[:5],
        "top_asks": asks[:5],
    }


def propose_paper_trade(market_slug: str, outcome: str, amount_usd: float, thesis: str) -> dict:
    """Return a pending paper-trade action for host approval/execution."""
    return {
        "pending": True,
        "action": "paper_trade",
        "params": {
            "market_slug": market_slug,
            "outcome": outcome,
            "amount_usd": amount_usd,
            "thesis": thesis,
        },
        "description": f"Paper trade {amount_usd:.2f} USD on {outcome} for {market_slug}",
    }


def create_watchlist_item(topic: str, market_slug: str, reason: str) -> dict:
    """Return a pending watchlist action for host approval/execution."""
    return {
        "pending": True,
        "action": "create_watchlist_item",
        "params": {"topic": topic, "market_slug": market_slug, "reason": reason},
        "description": f"Add {market_slug} to watchlist for {topic}",
    }
