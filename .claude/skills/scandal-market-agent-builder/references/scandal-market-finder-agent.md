# Scandal Market Finder Agent Reference

## Purpose

Build an Agent2 agent that scans Polymarket for markets whose prices could move after public scandals, reputation shocks, fandom narrative shifts, or social-media information cascades.

The agent does not search for current scandals and does not trade. It creates a watchlist for later sentinel agents.

## Agent2 Files

Create:

```text
agents/scandal-market-finder/
  __init__.py
  agent.py
  tools.py
  schemas.py
  main.py
  config.yaml
  Dockerfile
```

## Prompt Shape

Use five layers:

1. Identity: senior prediction-market researcher.
2. Workspace: Polymarket terminal, market detail sheet, query notepad.
3. Thinking process: outcome mechanics, entity exposure, scandal sensitivity, social surface, tradeability, watchability.
4. Examples: Eurovision, Oscars, political nominations, influencer cancellation, Fed-rate rejection.
5. Outcomes: `watchlist_created`, `needs_more_research`, `rejected`.

## Tools

Use read-only tools:

- `polymarket_recent_markets(limit)`
- `polymarket_search(query, limit)`
- `polymarket_market_detail(slug_or_id)`
- `suggest_watch_queries(market_title, description, entities)`

Do not add trade tools to this agent.

## Output Contract

Each accepted market should include:

- `market_title`
- `market_slug`
- `category`
- `entity_type`
- `entities`
- `why_scandal_reactive`
- `scandal_sensitivity`: `low`, `medium`, `high`
- `social_surface`: `low`, `medium`, `high`
- `tradeability`: `low`, `medium`, `high`
- `watch_priority`: `low`, `medium`, `high`
- `possible_catalysts`
- `watch_sources`
- `watch_queries`
- `next_agent_task`

## Good Markets

- Eurovision and public-vote contests.
- Awards such as Oscars, Grammys, sports awards.
- Political nomination or election markets where candidate reputation matters.
- Creator, influencer, streamer, brand, or cancellation markets.
- Album, movie, and entertainment markets where public attention affects outcome.

## Bad Markets

- Fed-rate and macro data markets.
- Weather markets.
- Purely technical/on-chain events.
- Calendar/deadline markets.
- Markets with no clear public entity.
- Markets already resolved or practically determined.

## Acceptance Criteria

- Returns watchlist only.
- Rejects factual/technical markets with reasons.
- Produces watch queries useful for a later sentinel.
- Does not create `pending_actions`.
- Does not recommend a trade.

