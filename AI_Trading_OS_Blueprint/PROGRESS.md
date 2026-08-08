# Progress

Current Status: Phase 1 Foundation — in progress

## 2026-08-07 — Phase 1 kickoff (M1.1–M1.4, M1.6 partial)

- Git repo initialized at `arcturus/`; monorepo layout established
  (`apps/web`, `services/api`, `infra/`, blueprint docs).
- Backend skeleton live: FastAPI app factory, lifespan management, typed
  pydantic-settings (`ARCTURUS_` prefix), structured logging, CORS,
  `/health` + `/health/ready`.
- Clean architecture layers in place: `domain` (pure models + ports),
  `application` (use cases), `infrastructure` (adapters), `api` (HTTP).
- First hexagonal port shipped: `MarketDataProvider` with Yahoo Finance
  adapter (quotes + OHLCV candles), provider registry, canonical
  `EXCHANGE:TICKER` symbols with vendor mapping quarantined in the adapter.
- Endpoints verified against live data:
  `GET /api/v1/market/quote/NSE:RELIANCE` → INR quote;
  `GET /api/v1/market/candles/NASDAQ:AAPL` → 251 daily candles.
- Infrastructure stack written: `infra/docker-compose.yml` with TimescaleDB,
  Redis, Qdrant, Neo4j, MinIO — healthchecks + named volumes.
- Quality gates green: 13 pytest tests, ruff (lint + format), mypy --strict.
- ADRs 001–006 recorded in DECISIONS.md.

Notes:
- Port 8000 is occupied by an unrelated app on the dev machine; dev server
  runs on 8600 (documented in README).
- A stale uv cache initially hid `librt` Windows wheels (transitive dep of
  mypy); fixed with `uv lock --refresh-package librt`. No pin needed.

## 2026-08-07 — M1.5 frontend skeleton

- Next.js 16.3 (App Router, TypeScript, Tailwind 4) scaffolded in `apps/web`.
- App shell: dark sidebar navigation listing all 16 product modules from the
  blueprint (Dashboard live; the rest visible but disabled until shipped).
- TanStack Query provider + typed API client (`src/lib/api.ts`) pointed at
  the FastAPI backend; Zustand workspace store carrying the selected-symbol
  context the AI copilot will later read.
- Dashboard page renders a live Market Pulse grid (NSE + NASDAQ quotes,
  60s refetch) through the provider adapter layer.
- `npm run build` and ESLint clean.

## 2026-08-07 — M1.7 persistence, Watchlists module, CI

- Docker infra stack running and healthy (TimescaleDB, Redis, Qdrant, Neo4j, MinIO).
- Persistence layer: async SQLAlchemy engine/session management, ORM rows kept
  separate from domain models, Alembic async migrations (0001 applied).
- Watchlist vertical slice shipped end-to-end: domain (models/port/errors) →
  service → SQLAlchemy repository → REST CRUD → Next.js Watchlists page with
  live quote cards. Second module live in the sidebar.
- `/health/ready` now probes the DB and reports 503/degraded when it's down.
- GitHub Actions CI written (backend + frontend jobs) — needs a GitHub remote.
- Quality gates: 23 pytest tests, ruff, mypy --strict, next build, eslint.

Phase 1 Foundation is functionally complete. Repo pushed to GitHub over SSH
(git@github.com:the-sasi/arcturus.git).

## 2026-08-08 — Data expansion: profile, fundamentals, news + Stock Workspace

- Two new hexagonal ports: `FundamentalDataProvider`, `NewsProvider` — each
  capability independently swappable via settings (`ARCTURUS_FUNDAMENTAL_DATA_PROVIDER`,
  `ARCTURUS_NEWS_PROVIDER`).
- Yahoo adapter now implements all three ports. Vendor payload parsing isolated
  in pure functions (`yahoo/parsers.py`) — unit-tested against fixtures,
  defensive against Yahoo's shape drift (legacy flat + nested news formats).
- New domain models: `CompanyProfile`, `Fundamentals` (15 typed metrics +
  `extras` carrying analyst recommendation, target price, growth rates, etc.),
  `NewsArticle`.
- New endpoints: `/api/v1/market/profile|fundamentals|news/{symbol}`.
- Frontend Stock Workspace page (third live module): symbol search synced to
  the Zustand workspace store, fundamentals grid, company profile, live quote,
  news feed.
- Verified live: RELIANCE profile (404k employees), fundamentals (₹18.06T mcap,
  PE 24.15, rec strong_buy), 5 real news articles.
- 31 tests green; ruff, mypy --strict, next build, eslint clean.

Remaining data integrations (blocked on user-provided API keys): Finnhub,
Alpha Vantage, NewsAPI; Upstox/Zerodha arrive with Phase 4 broker work.

## 2026-08-09 — Speed + in-app news reader + full Docker deployment

- Redis read-through caching in application services (fail-open): quotes 30s,
  candles 5m, profile/fundamentals 1h, news 5m, extracted articles 24h.
  User requirement: "system should be fast" — latency is now a first-class
  concern.
- In-app news reading: `ArticleReader` port + trafilatura adapter (httpx,
  8s timeout, 3MB cap, SSRF guard rejecting non-public hosts). Endpoint
  `GET /api/v1/market/news/article?url=`. Workspace news items open a
  reader modal with hero image, extracted text, fallback to Yahoo summary.
- News thumbnails: Yahoo thumbnail renditions parsed (smallest ≥200px).
- Fixed dividend-yield double-percent bug (Yahoo reports percent already).
- Full Docker deployment: `services/api/Dockerfile` (uv, auto-migrations on
  start), `apps/web/Dockerfile` (standalone Next build), both added to
  infra/docker-compose.yml (api on 8600, web on 3000).
- README now carries the complete architecture + external-calls table;
  standing rule: update it in the same commit as any code change.
- 46 tests green; all quality gates clean.

## 2026-08-09 — Stock directory: browse the whole market (for beginners)

- Instruments table (migration 0002) seeded from official exchange listings:
  NSE EQUITY_L.csv (2,369 equities) + Nasdaq Trader symbol directory
  (8,809 NASDAQ/NYSE/AMEX stocks & ETFs) = 11,178 instruments.
- New ports: InstrumentDirectoryProvider (per-exchange listing fetchers,
  fail-independent sync) + InstrumentRepository (search/paginate/upsert).
- Endpoints: GET /api/v1/instruments (search by name/ticker, exchange filter,
  pagination), POST /api/v1/instruments/sync.
- Market Intelligence module is live (4th page): full stock explorer —
  search "tata" → 13 NSE companies; click any row → Stock Workspace.
- Workspace symbol input replaced with name-based autocomplete + popular
  stock chips (Reliance, TCS, Apple, Nvidia, …) for newcomers.
- 54 tests green; all gates clean; full stack redeployed in Docker.

## 2026-08-09 — Dashboard rebuilt as a morning briefing

- Index strip: NIFTY 50, SENSEX, S&P 500, NASDAQ live cards
  (new INDEX exchange; Yahoo-native ^ tickers pass through the adapter).
- Watchlist-aware pulse: shows the user's first non-empty watchlist
  (fallback: curated Market Pulse), each card click-through to Workspace.
- Top gainers/losers: GET /api/v1/market/movers over a curated NIFTY-50 +
  US-majors universe (concurrent quotes, semaphore 8, fail-soft per symbol,
  60s Redis TTL — measured 6s cold / 43ms cached, 49/50 quoted).
- Market headlines: merged index-level news (^NSEI + ^GSPC) with thumbnails
  and the in-app article reader.
- 57 tests green; all gates clean; redeployed in Docker.

## 2026-08-09 — Dashboard charts

- Hero index chart: TradingView Lightweight Charts (open-source renderer;
  data flows through OUR candles endpoint + Redis cache, no vendor iframe).
  Index selector (NIFTY/SENSEX/S&P/NASDAQ) × range toggle (1D/1M/1Y).
- 30-day SVG sparklines inside every index and quote card (zero-dependency
  inline polyline; polarity color paired with signed number per a11y rule).
- India essentials strip: USD/INR, Gold (COMEX), Brent — Yahoo-native
  tickers through the INDEX passthrough.
- Market breadth bar: advancing/declining counts added to MoversSnapshot.
- Polarity palette checked with the dataviz validator: red/green deutan
  ΔE 6.5 → acceptable only with secondary encoding, which every element
  has (▲/▼, signed numbers, slope shape).
- 57 tests green; gates clean; redeployed in Docker.

## 2026-08-09 — Phase 2 STARTED: M2.1 indicator library + Workspace chart

- Deterministic indicator library in the domain layer (`domain/indicators/`):
  SMA, EMA (SMA-seeded), RSI (Wilder), MACD (line/signal/histogram),
  Bollinger bands — pure functions with golden-value tests. Per the
  blueprint: LLMs will cite these values, never compute them.
- `GET /api/v1/market/indicators/{symbol}?specs=ema:20,rsi:14` — validated
  spec grammar (422 on unknown), series aligned 1:1 with candle timestamps.
- Stock Workspace now has a real price chart: candlesticks + volume,
  EMA20/EMA50 overlays with legend, RSI(14) pane with 30/70 bands,
  ranges 1D/6M/1Y/3Y (Lightweight Charts, our data only).
- Verified live: RELIANCE EMA20 1300.97 < EMA50 1310.43, RSI 58.6.
- Dev-mode volumes proved out: backend changes needed zero rebuilds
  (one web-container restart for Turbopack to see the new module).
- 71 tests green; all gates clean.
- News multi-source expansion consciously deferred to backlog in favor of
  Phase 2 (Yahoo adequate for now; port already exists).

## 2026-08-09 — M2.2 Strategy Engine core

- Strategy plugin framework (`domain/strategy/`): deterministic, versioned
  plugins producing StrategyVerdict — stance (bullish/neutral/bearish),
  confidence 0-100 (rule-scored heuristic, explicitly NOT win probability),
  entry zone, ATR-based stop, and number-backed plain-language reasons.
  No blind Buy/Sell — verdicts feed the future Decision Engine.
- Tier 1 plugins: EMA 20/50 crossover (freshness/price/volume confirmation),
  RSI mean-reversion (oversold-in-uptrend filter — no edge in downtrends),
  20-day range breakout (volume-confirmed; unconfirmed breakouts stay neutral).
- ATR (Wilder) added to indicator library; RSI flat-series edge case fixed
  (was 100, now neutral 50).
- Endpoints: GET /api/v1/strategies, /strategies/evaluate/{symbol}.
- Workspace Strategy Analysis panel: verdict cards with confidence bars,
  entry/stop, expandable reasons, and a decision-support disclaimer.
- Verified live on RELIANCE: bearish EMA structure (62 sessions old),
  RSI 58.6 no setup, coiling 0.8% under the 20-day high — coherent reads.
- 80 tests green (9 golden strategy scenarios); all gates clean.
- Next: M2.2b — backtester with realistic costs + walk-forward validation,
  regime filter, position sizing; then Tier 2 quant strategies.
