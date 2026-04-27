"""Read-only Polymarket tools for scandal-reactive market discovery."""
from __future__ import annotations

import json
import re
from typing import Any

import httpx


GAMMA_BASE = "https://gamma-api.polymarket.com"
USER_AGENT = "agent2-scandal-market-finder/0.2.0"


def _client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
        },
        timeout=20.0,
        follow_redirects=True,
    )


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


def _compact_market(market: dict[str, Any]) -> dict[str, Any]:
    prices = [_as_float(item) for item in _parse_json_list(market.get("outcomePrices"))]
    return {
        "id": market.get("id", ""),
        "slug": market.get("slug", ""),
        "question": market.get("question", ""),
        "description": (market.get("description") or "")[:1200],
        "outcomes": _parse_json_list(market.get("outcomes")),
        "prices": prices,
        "volume": _as_float(market.get("volume") or market.get("volumeNum")) or 0.0,
        "volume24hr": _as_float(market.get("volume24hr")) or 0.0,
        "liquidity": _as_float(market.get("liquidity") or market.get("liquidityNum")) or 0.0,
        "end_date": market.get("endDate", ""),
        "category": market.get("category", ""),
        "tags": market.get("tags", []),
    }


def polymarket_recent_markets(limit: int = 50) -> dict[str, Any]:
    """Return active Polymarket markets ordered by recent 24h volume."""
    limit = max(1, min(limit, 100))
    params = {
        "active": "true",
        "closed": "false",
        "archived": "false",
        "limit": limit,
        "order": "volume24hr",
        "ascending": "false",
    }
    with _client() as client:
        response = client.get(f"{GAMMA_BASE}/markets", params=params)
        response.raise_for_status()
        markets = response.json()
    return {"ok": True, "markets": [_compact_market(m) for m in markets]}


def polymarket_search(query: str, limit: int = 20) -> dict[str, Any]:
    """Search active Polymarket markets by terms in question, description, or slug."""
    limit = max(1, min(limit, 50))
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

    terms = [term.lower() for term in re.split(r"\s+", query) if term.strip()]
    matched: list[dict[str, Any]] = []
    for market in markets:
        haystack = " ".join(
            str(market.get(key, "")) for key in ("question", "description", "slug", "category")
        ).lower()
        if terms and not all(term in haystack for term in terms):
            continue
        matched.append(_compact_market(market))
        if len(matched) >= limit:
            break
    return {"ok": True, "query": query, "markets": matched}


def polymarket_market_detail(slug_or_id: str) -> dict[str, Any]:
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
    compact = _compact_market(market) if market else {}
    compact["ok"] = bool(market)
    compact["clob_token_ids"] = _parse_json_list(market.get("clobTokenIds")) if market else []
    return compact


def suggest_watch_queries(market_title: str, description: str = "", entities: list[str] | None = None) -> dict[str, Any]:
    """Suggest public social/news queries for a market and its entities."""
    entities = [item.strip() for item in (entities or []) if item.strip()]
    if not entities:
        words = re.findall(r"[A-Z][A-Za-z0-9'’-]{2,}", f"{market_title} {description}")
        stop = {"Will", "Who", "What", "When", "Where", "The", "This", "That"}
        entities = []
        for word in words:
            if word not in stop and word not in entities:
                entities.append(word)
            if len(entities) >= 6:
                break

    catalysts = [
        "scandal",
        "controversy",
        "backlash",
        "accusation",
        "apology",
        "disqualified",
        "removed",
        "boycott",
    ]
    queries: list[str] = []
    for entity in entities[:8]:
        for catalyst in catalysts[:5]:
            queries.append(f"{entity} {catalyst}")
    if not queries:
        base = re.sub(r"[^A-Za-z0-9 ]+", " ", market_title).strip()
        queries = [f"{base} scandal", f"{base} controversy", f"{base} backlash"]

    return {
        "ok": True,
        "entities": entities,
        "watch_sources": ["Reddit", "Google News", "X search", "TikTok search", "fan/community blogs"],
        "watch_queries": queries[:30],
        "possible_catalysts": catalysts,
    }
