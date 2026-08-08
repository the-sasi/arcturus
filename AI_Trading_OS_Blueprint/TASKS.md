# Tasks

## Phase 2 — Decision Engine

### M2.2b remaining (next)
- [ ] Regime filter (index vs 200-DMA, breadth) gating strategy confidence
- [ ] Volatility-based position sizing suggestions
- [ ] Strategy signal markers on the Workspace chart
- [ ] Tier 2 strategies: cross-sectional momentum, multi-factor ranking, pairs

### Done (2026-08-09) — M2.2b Backtester
- [x] ADR-007: custom prefix-replay engine (one source of truth; no-lookahead
      by construction) over OSS engines requiring rule duplication
- [x] Engine: next-open fills, intraday ATR stops with gap handling,
      signal-flip exits, per-side costs, equity curve
- [x] Metrics: return vs buy&hold, win rate, avg win/loss, max drawdown,
      exposure, annualized Sharpe
- [x] GET /api/v1/strategies/backtest/{symbol}?strategy=key (Redis 1h)
- [x] Workspace Backtests panel (3y table per strategy, cost disclaimer)
- [x] 7 hand-checkable engine tests via scripted strategy

### Done (2026-08-09) — M2.2 Strategy Engine core
- [x] Strategy plugin contract (deterministic, versioned; stance/confidence/
      entry/stop/reasons — no blind buy/sell per blueprint)
- [x] EMA crossover, RSI mean-reversion, 20-day range breakout plugins
- [x] ATR added to indicator library (stop calculation)
- [x] GET /api/v1/strategies + /strategies/evaluate/{symbol}
- [x] Workspace Strategy Analysis panel with verdict cards + disclaimer
- [x] Golden scenario tests on synthetic histories (9 scenarios)

### M2.3 Market Intelligence Tier 1
- [ ] Market-wide movers pipeline (beyond curated 50)
- [ ] Sector heatmap; screeners on fundamentals; index breadth

### Done (2026-08-09) — M2.1 Indicators + Workspace chart
- [x] Indicator library: SMA/EMA/RSI/MACD/Bollinger (pure, golden-tested)
- [x] GET /api/v1/market/indicators/{symbol} with spec grammar validation
- [x] Workspace candlestick chart: volume, EMA20/50 overlays, RSI pane, 4 ranges

## Phase 1 — Foundation

### Remaining (Phase 1 wrap-up)
- [ ] Push repo to GitHub (CI workflow is ready but has nowhere to run)
- [ ] Redis quote caching in the market data path (30–60s TTL)
- [ ] Redis readiness probe once the client lands
- [ ] Instruments table (deferred from M1.7 — watchlists ship first;
      instruments land with the strategy engine's data needs in Phase 2)

### Data integrations awaiting API keys (ask user to register)
- [ ] Finnhub adapter (real-time US quotes, earnings calendar) — needs FINNHUB_API_KEY
- [ ] NewsAPI adapter (broad news coverage) — needs NEWSAPI_KEY
- [ ] Alpha Vantage adapter (fundamentals cross-check) — needs ALPHAVANTAGE_KEY

## Done (2026-08-09)

### Dashboard charts
- [x] Hero index chart (Lightweight Charts, own data feed, index × range toggles)
- [x] Sparklines in all index/quote cards (inline SVG)
- [x] Essentials strip: USD/INR, Gold, Brent
- [x] Breadth bar (advancing/declining in MoversSnapshot)

### Dashboard morning briefing
- [x] INDEX exchange + Yahoo index-ticker passthrough (^NSEI, ^GSPC, …)
- [x] GET /api/v1/market/movers — curated universe, concurrent, cached 60s
- [x] Dashboard: index strip, watchlist-aware pulse, gainers/losers,
      market headlines with in-app reader

### Stock directory + Market Intelligence explorer
- [x] Instruments table (migration 0002) + repository port/adapter
- [x] Exchange directory adapters: NSE CSV + Nasdaq Trader (11,178 instruments seeded)
- [x] GET /api/v1/instruments (search/filter/paginate) + POST /instruments/sync
- [x] Market Intelligence page: browse/search whole market, click-through to Workspace
- [x] Workspace autocomplete by company name + popular-stock chips

### Speed + in-app reader + Docker deployment
- [x] Redis read-through cache (fail-open) across market/research services
- [x] ArticleReader port + trafilatura adapter, SSRF-guarded, 24h article cache
- [x] `GET /api/v1/market/news/article?url=` + in-app reader modal with images
- [x] News thumbnails from Yahoo renditions
- [x] Dividend-yield double-percent fix
- [x] Dockerfiles for api (uv + auto-migrate) and web (standalone Next)
- [x] api + web services in docker-compose (full stack in Docker)
- [x] README: complete architecture + external-calls table (standing rule)

## Done (2026-08-08)

### Data expansion (Yahoo full extraction) + Stock Workspace
- [x] Ports: FundamentalDataProvider, NewsProvider (per-capability provider config)
- [x] Yahoo adapter: profile, fundamentals (15 typed metrics + extras), news
- [x] Pure vendor parsers with fixture tests (both Yahoo news shapes)
- [x] Endpoints: /api/v1/market/profile|fundamentals|news/{symbol}
- [x] Stock Workspace page: search, fundamentals grid, about, quote, news
- [x] Verified live against NSE:RELIANCE; 31 tests green

## Done (2026-08-07)

### M1.7 Persistence + Watchlists + CI
- [x] SQLAlchemy async engine + session factory (`infrastructure/db/engine.py`)
- [x] ORM models separate from domain models; naming conventions for Alembic
- [x] `WatchlistRepository` port + SQLAlchemy adapter (+ in-memory fake for tests)
- [x] Alembic async env + migration 0001 (watchlists, watchlist_items) applied
- [x] REST CRUD: `/api/v1/watchlists` (+items add/remove), domain errors → 404/409
- [x] `/health/ready` now probes the database (503/degraded when down)
- [x] 10 new tests (service + repository via aiosqlite) — 23 total green
- [x] Frontend Watchlists page: create/delete lists, add/remove symbols with
      live QuoteCards; sidebar entry enabled
- [x] GitHub Actions CI: backend (ruff, mypy, pytest) + frontend (eslint, build)
- [x] End-to-end verified: CRUD against TimescaleDB, symbol normalization,
      persistence across requests

### M1.1 Repo + layout
- [x] Initialize git repo at `arcturus/`
- [x] Monorepo layout: `apps/web`, `services/api`, `infra/`
- [x] Root README, .gitignore, .editorconfig

### M1.2 Backend skeleton
- [x] FastAPI app factory with lifespan management
- [x] Layered structure: `domain/`, `application/`, `infrastructure/`, `api/`
- [x] Typed settings via pydantic-settings (.env driven)
- [x] `/health` liveness + `/health/ready` readiness endpoints
- [x] Structured logging setup

### M1.3 Market data port
- [x] Domain models: Instrument, Quote, Candle, Symbol, AssetClass, Exchange, Interval
- [x] `MarketDataProvider` port (abstract interface)
- [x] Yahoo Finance adapter (yfinance) — quotes + historical OHLCV
- [x] Provider registry for runtime adapter selection
- [x] REST endpoints: `/api/v1/market/quote/{symbol}`, `/api/v1/market/candles/{symbol}`
- [x] Verified against live data (NSE:RELIANCE quote, NASDAQ:AAPL candles)

### M1.4 Infrastructure stack
- [x] docker-compose.yml: TimescaleDB, Redis, Qdrant, Neo4j, MinIO
- [x] Healthchecks + named volumes for all services
- [x] .env.example files (infra + api)

### M1.5 Frontend skeleton
- [x] Next.js 16.3 (App Router) + TypeScript + Tailwind 4
- [x] App shell: sidebar navigation for all 16 product modules
- [x] TanStack Query + Zustand wiring
- [x] Typed API client pointed at FastAPI backend
- [x] Dashboard with live Market Pulse quotes; build + lint clean

### M1.6 Test harness
- [x] pytest — 13 tests (domain, adapter mapping, registry, API health)
- [x] Ruff lint + format (clean)
- [x] mypy strict (clean)
