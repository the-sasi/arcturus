# Product Backlog

Future ideas and enhancements.

## Market Intelligence — from directory to actual intelligence

Agreed 2026-08-09: today the page is a stock directory/explorer; the roadmap
below is what earns the "Intelligence" name. Hierarchy: data → screening →
synthesis → judgment.

### Tier 1 — deterministic, no AI needed (build with/just before Phase 2)
- [ ] Movers & shakers: top gainers/losers, unusual volume, 52w high/low
      breakouts — computed from candle data we already fetch
- [ ] Sector heatmap: sector-level performance today (sector comes from
      company profiles), teaches sector rotation
- [ ] Screeners: filter universe on fundamentals we already serve
      (e.g. P/E < 20, profit margin > 10%, volume rising)
- [ ] Index & breadth: NIFTY/S&P levels, advance-decline ratio (risk-on/off)

### Tier 2 — needs News Intelligence + RAG (Phase 3)
- [ ] Market narrative: News Agent digests headlines (article extraction
      already built) → daily "what's moving markets and why" summary
- [ ] Event radar: upcoming earnings, RBI/Fed meetings, dividends for
      held/watched stocks

### Tier 3 — agent layer (Phases 3–4)
- [ ] Anomaly callouts: Correlation/Liquidity agents flag "X moving on 4×
      volume with no news"
- [ ] Regime detection: Macro agent labels the environment (trending/choppy,
      risk-on/off); Decision Engine uses it to judge strategy fit

Interim option if the name bothers us before Tier 1 ships: rename sidebar
entry to "Explore Market".

## Stock Workspace — planned growth
- [ ] Price charts (TradingView) with indicators — candle data already in API
- [ ] AI copilot anchored to workspace context (Zustand store already carries
      selected symbol for this)
- [ ] Decision hooks: "analyze with my strategy", "add to journal"

## News breadth — multi-source pipeline (deferred 2026-08-09 in favor of Phase 2)

Yahoo-only news is shallow and US-tilted. Plan when picked up:
- [ ] RSS adapter behind the existing NewsProvider port: Economic Times,
      Moneycontrol, LiveMint, Business Standard + global macro feeds
- [ ] Google News RSS per-company query (free, no key, huge breadth)
- [ ] NSE corporate announcements feed (official filings — high signal)
- [ ] CompositeNewsProvider: concurrent fan-out, dedupe near-identical
      headlines, recency sort, Redis 5m TTL
- [ ] Later with keys: Finnhub (sentiment), Marketaux, NewsAPI
This merged stream is also the raw input for Phase 3 News Intelligence RAG.

## Other captured ideas
- [ ] Scheduled instrument-directory re-sync (listings change; ~monthly)
- [ ] Provider adapters awaiting user API keys: Finnhub, NewsAPI, Alpha Vantage
