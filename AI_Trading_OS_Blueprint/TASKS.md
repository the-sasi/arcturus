# Tasks

## Phase 1 — Foundation

### M1.7 Persistence
- [ ] SQLAlchemy async engine + session management
- [ ] Alembic migrations
- [ ] Instruments + watchlists tables

### Remaining
- [ ] GitHub Actions CI (lint + typecheck + tests)
- [ ] Readiness probes for TimescaleDB/Redis once clients land

## Done (2026-08-07)

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
