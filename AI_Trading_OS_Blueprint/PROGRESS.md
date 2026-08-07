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

Next: M1.7 persistence (SQLAlchemy + Alembic), then GitHub Actions CI.
