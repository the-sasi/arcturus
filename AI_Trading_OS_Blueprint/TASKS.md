# Tasks

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
