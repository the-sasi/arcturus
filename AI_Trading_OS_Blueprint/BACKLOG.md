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

## External data providers — public-apis sweep (2026-08-17)

Swept the 1,737 entries in github.com/public-apis/public-apis against our needs
(Indian equities, swing trading, explainable + reproducible). Findings:

**The structural fact:** there is no free, keyless API for Indian equity OHLCV in
that list. The Finance section is overwhelmingly US equities, US filings, and
payments. For NSE/BSE the realistic universe is: Yahoo (what we use), NSE's own
public files (we already use for the instrument directory), and **broker APIs**.

Shortlisted candidates, each with the trigger that would make it worth building
(ADR-009: nothing is adopted before its trigger fires):

| Candidate | What it gives us | Trigger to adopt |
|---|---|---|
| **Angel One SmartAPI** (`smartapi.angelbroking.com`) | India-native live + historical NSE/BSE candles AND order execution behind one account. Highest-value single integration in the whole list for us. | Phase 4 (paper→live). Also revisit sooner if Yahoo's Indian data proves unreliable in R2. Needs a demat account. |
| **Twelve Data** | Second opinion on NSE/BSE daily bars — cross-source candle validation. | Only if R2's deterministic checks prove insufficient, i.e. we find bad bars that single-source validation cannot detect (e.g. silently rewritten split-adjusted history). |
| **MarketAux** / **StockData** | Market news with *tagged tickers* + sentiment — solves the symbol-attribution problem in our news pipeline. | When the multi-source news pipeline is picked up (see "News breadth" above). |
| **Frankfurter** / **currency-api** | Keyless FX (ECB-sourced) for the USD/INR essentials tile. | Only if Yahoo's FX quote proves flaky. Yahoo covers it today. |
| **FRED** (free key) | Macro series (rates, CPI, yield curve) for a macro-aware regime model. | When regime detection outgrows the 200-DMA rule and we have evidence the rule is insufficient. |
| **OpenFIGI** | Cross-provider instrument identifier mapping. | Only when a second market-data provider exists and symbols must be reconciled. |
| **data.gov.in** (API Setu / Open Government India) | Indian official economic datasets. | No current use case. |

**Explicitly rejected** (not "later" — wrong for this product): NORTH7 signals,
Top 5 Stocks AI watchlists, Styvio, WallstreetBets sentiment, and similar
black-box signal feeds. A recommendation we cannot reproduce or explain violates
the core vision. Same reasoning excludes Portfolio Optimizer for the future
allocation layer: position sizing must be our own deterministic, auditable math.

**Not applicable:** Alpaca, Polygon, IEX Cloud, Tradier, Financial Modeling Prep,
SEC EDGAR + all US-filing APIs (Edgrapi, StockFit, Filingrail, Aletheia),
CongressInvests — US-only coverage. Indian Mutual Fund (mfapi.in) is keyless and
complete but we do not cover mutual funds.

Carried forward from earlier: Finnhub, NewsAPI, Alpha Vantage adapters remain
blocked on API keys (Alpha Vantage's free tier is now very restrictive — verify
current limits before building).
