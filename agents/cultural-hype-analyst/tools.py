"""Read-only social and Polymarket tools for cultural hype analysis."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx


REDDIT_BASE = "https://www.reddit.com"
GAMMA_BASE = "https://gamma-api.polymarket.com"
USER_AGENT = os.environ.get(
    "REDDIT_RO_USER_AGENT",
    "script:agent2-cultural-hype-analyst:v0.2.0",
)


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


def reddit_search(subreddit: str, query: str, limit: int = 10, sort: str = "new", time: str = "week") -> dict:
    """Search public Reddit posts in one subreddit or across all."""
    scope = subreddit.strip().strip("/").removeprefix("r/")
    limit = max(1, min(limit, 25))
    if scope.lower() == "all":
        path = "/search.json"
        params = {"q": query, "limit": limit, "sort": sort, "t": time}
    else:
        path = f"/r/{scope}/search.json"
        params = {"q": query, "restrict_sr": "1", "limit": limit, "sort": sort, "t": time}

    with _client() as client:
        response = client.get(f"{REDDIT_BASE}{path}", params=params)
        response.raise_for_status()
        data = response.json()

    posts = []
    for child in data.get("data", {}).get("children", []):
        item = child.get("data", {})
        posts.append({
            "id": item.get("id", ""),
            "subreddit": item.get("subreddit", scope),
            "title": item.get("title", ""),
            "score": item.get("score", 0),
            "num_comments": item.get("num_comments", 0),
            "created_utc": item.get("created_utc", 0),
            "permalink": f"{REDDIT_BASE}{item.get('permalink', '')}",
            "url": item.get("url", ""),
            "selftext_snippet": (item.get("selftext") or "")[:700],
        })
    return {"ok": True, "subreddit": scope, "query": query, "posts": posts}


def reddit_posts(subreddit: str, sort: str = "hot", limit: int = 10, time: str = "week") -> dict:
    """List public Reddit posts for a community."""
    scope = subreddit.strip().strip("/").removeprefix("r/")
    limit = max(1, min(limit, 25))
    params = {"limit": limit}
    if sort in {"top", "controversial"}:
        params["t"] = time
    with _client() as client:
        response = client.get(f"{REDDIT_BASE}/r/{scope}/{sort}.json", params=params)
        response.raise_for_status()
        data = response.json()
    posts = []
    for child in data.get("data", {}).get("children", []):
        item = child.get("data", {})
        posts.append({
            "id": item.get("id", ""),
            "subreddit": item.get("subreddit", scope),
            "title": item.get("title", ""),
            "score": item.get("score", 0),
            "num_comments": item.get("num_comments", 0),
            "permalink": f"{REDDIT_BASE}{item.get('permalink', '')}",
            "selftext_snippet": (item.get("selftext") or "")[:700],
        })
    return {"ok": True, "subreddit": scope, "sort": sort, "posts": posts}


def polymarket_search(query: str, limit: int = 10) -> dict:
    """Search active Polymarket markets and return compact candidates."""
    limit = max(1, min(limit, 30))
    params = {
        "active": "true",
        "closed": "false",
        "archived": "false",
        "limit": 200,
        "order": "volume24hr",
        "ascending": "false",
    }
    with _client() as client:
        response = client.get(f"{GAMMA_BASE}/markets", params=params)
        response.raise_for_status()
        markets = response.json()

    terms = [term.lower() for term in query.split() if term.strip()]
    matched = []
    for market in markets:
        haystack = " ".join(str(market.get(key, "")) for key in ("question", "description", "slug")).lower()
        if terms and not all(term in haystack for term in terms):
            continue
        prices = [_as_float(item) for item in _parse_json_list(market.get("outcomePrices"))]
        matched.append({
            "id": market.get("id", ""),
            "slug": market.get("slug", ""),
            "question": market.get("question", ""),
            "description": (market.get("description") or "")[:1000],
            "yes_price": prices[0] if prices else None,
            "no_price": prices[1] if len(prices) > 1 else None,
            "volume": _as_float(market.get("volume") or market.get("volumeNum")) or 0.0,
            "volume24hr": _as_float(market.get("volume24hr")) or 0.0,
            "liquidity": _as_float(market.get("liquidity") or market.get("liquidityNum")) or 0.0,
            "end_date": market.get("endDate", ""),
        })
        if len(matched) >= limit:
            break
    return {"ok": True, "query": query, "markets": matched}


def polymarket_market_detail(slug_or_id: str) -> dict:
    """Fetch one Polymarket market by slug or numeric id."""
    value = slug_or_id.strip()
    with _client() as client:
        if value.isdigit():
            response = client.get(f"{GAMMA_BASE}/markets/{value}")
            response.raise_for_status()
            market = response.json()
        else:
            response = client.get(f"{GAMMA_BASE}/markets", params={"slug": value, "limit": 1})
            response.raise_for_status()
            data = response.json()
            market = data[0] if data else {}
    prices = [_as_float(item) for item in _parse_json_list(market.get("outcomePrices"))]
    return {
        "ok": bool(market),
        "id": market.get("id", ""),
        "slug": market.get("slug", ""),
        "question": market.get("question", ""),
        "description": market.get("description", ""),
        "outcomes": _parse_json_list(market.get("outcomes")),
        "prices": prices,
        "clob_token_ids": _parse_json_list(market.get("clobTokenIds")),
        "volume": _as_float(market.get("volume") or market.get("volumeNum")) or 0.0,
        "liquidity": _as_float(market.get("liquidity") or market.get("liquidityNum")) or 0.0,
        "end_date": market.get("endDate", ""),
    }


def propose_paper_trade(market_slug: str, outcome: str, amount_usd: float, thesis: str) -> dict:
    """Return a pending paper trade action; this never places a real or paper order by itself."""
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
