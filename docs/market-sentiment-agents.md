# Market Sentiment Agents

Three Agent2 MVP agents implement the social-to-Polymarket workflow.

## 1. Cultural Hype Analyst

Use for culture, fandom, Eurovision, music, albums, films, awards, games, and
public-attention markets.

Flow:

```text
topic -> Reddit evidence -> hype ranking -> Polymarket matches -> paper-trade suggestion
```

Local service:

```bash
docker compose build cultural-hype-analyst
docker compose up -d redis cultural-hype-analyst
```

Example request:

```bash
curl -X POST "http://localhost:8010/tasks?mode=sync" \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "topic": "Eurovision 2026",
      "communities": ["eurovision"],
      "market_query": "Eurovision"
    }
  }'
```

## 2. Market Research Desk

Use for the multi-role desk flow: social scout, market matcher, thesis analyst,
and paper trader.

Flow:

```text
topic + communities
  -> Social Scout checks communities
  -> Market Matcher finds Polymarket markets
  -> Thesis Analyst writes bull/bear/resolution risks
  -> Paper Trader proposes only pending paper actions
```

Local service:

```bash
docker compose build market-research-desk
docker compose up -d redis market-research-desk
```

Example request:

```bash
curl -X POST "http://localhost:8011/tasks?mode=sync" \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "topic": "Trump Iran ceasefire",
      "subreddits": "democrats,Republican,conservative,neoliberal",
      "market_query": "Iran Trump"
    }
  }'
```

## 3. Scandal Market Finder

Use for market-first discovery: find Polymarket markets that are likely to move
when future public scandals, reputation shocks, fandom narratives, or social
media backlash appear.

Flow:

```text
Polymarket scan -> entity detection -> scandal-reactivity judgment -> sentinel watchlist
```

Local service:

```bash
docker compose build scandal-market-finder
docker compose up -d redis scandal-market-finder
```

Example request:

```bash
curl -X POST "http://localhost:8012/tasks?mode=sync" \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Scanne Polymarket nach scandal-reactive Märkten für Kultur, Politik, Creator, Awards und Sport. Erstelle eine priorisierte Watchlist."
  }'
```

## Safety

All agents are read-only for public data sources. The scandal market finder does
not trade and does not create pending actions. Paper trades in the other agents
are returned as `pending_actions` so a host or human can decide what to execute.
