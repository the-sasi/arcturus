# Arcturus — AI Trading Operating System

An AI-first Decision Intelligence Platform for traders. Not a bot, not a signal
service — a complete trading workspace where every recommendation is explainable,
reproducible, evidence-based, and auditable.

> LLMs reason. Deterministic tools calculate.

> **Maintenance rule:** this README's Architecture and External Calls sections
> must be updated in the same commit as any code change that affects them.

## Repository layout

```
apps/web                  Next.js frontend (TypeScript, Tailwind)
services/api              FastAPI backend — modular monolith, clean architecture
infra/                    Docker Compose stack (databases + api + web)
AI_Trading_OS_Blueprint/  Living specification: vision, roadmap, tasks, ADRs
.github/workflows/        CI (backend + frontend gates)
```

## Quick start (everything in Docker)

Prerequisite: Docker Desktop running.

```bash
cd infra
cp .env.example .env   # first time only
docker compose up -d   # DEV mode (default): source bind-mounted, hot reload,
                       # no rebuilds — docker-compose.override.yml does this
```

Code changes apply instantly: uvicorn reloads the API (WatchFiles polling),
Next.js dev server reloads the UI. Rebuild only when dependencies change
(`docker compose up -d --build`, or delete the `web-node-modules` volume after
frontend dependency changes).

Production-style run (no mounts, optimized builds — ignores the override):

```bash
docker compose -f docker-compose.yml up -d --build
```

| Service | URL |
|---|---|
| Web app | http://localhost:3000 |
| API + docs | http://localhost:8600 · http://localhost:8600/docs |
| Neo4j browser | http://localhost:7474 |
| MinIO console | http://localhost:9001 |

Dev mode (hot reload, instead of the api/web containers):

```bash
cd services/api && uv sync && uv run uvicorn arcturus_api.main:app --reload --port 8600
cd apps/web && npm install && npm run dev
```

## Current architecture

```
Browser (localhost:3000)
  │  TanStack Query polling + Zustand workspace context
  ▼
Next.js 16 web (Docker: web)                       Live pages:
  │  REST, JSON                                    Dashboard (indices+charts, movers,
  │  charts: Lightweight Charts + inline SVG       breadth, headlines) · Market
  ▼  sparklines — fed by OUR endpoints only        Intelligence · Stock Workspace · Watchlists
FastAPI api (Docker: api, host port 8600)
  │
  ├─ api/          versioned HTTP layer, domain errors → 4xx/5xx
  ├─ application/  use-case services + Redis read-through caching
  │     MarketDataService      quotes incl. indices (TTL 30s) · candles (TTL 5m)
  │                            · movers over curated universe (TTL 60s)
  │     ResearchDataService    profile/fundamentals (TTL 1h) · news (TTL 5m)
  │                            · article reader (TTL 24h)
  │     WatchlistService       watchlist CRUD (no cache — source of truth is ours)
  │     InstrumentDirectoryService  browse/search 11k+ listed stocks; sync from exchanges
  │     IndicatorService       deterministic TA (sma/ema/rsi/macd/bollinger/atr) over cached candles
  │     StrategyService        versioned strategy plugins -> explainable verdicts
  │                            (ema_crossover · rsi_mean_reversion · range_breakout)
  │     BacktestService        prefix-replay backtests, realistic costs, 1h cache
  ├─ domain/       pure models + ports (zero framework/vendor imports)
  │     ports: MarketDataProvider · FundamentalDataProvider · NewsProvider
  │            · ArticleReader · InstrumentDirectoryProvider · InstrumentRepository
  │            · WatchlistRepository · CachePort
  └─ infrastructure/  adapters (the ONLY layer touching vendors)
        yahoo (yfinance)      → implements market/fundamental/news ports
        trafilatura reader    → reader-mode article extraction + SSRF guard
        exchange directories  → NSE EQUITY_L.csv + Nasdaq Trader symbol files
        redis cache           → fail-open JSON cache
        sqlalchemy repos      → watchlists + instruments in TimescaleDB (Alembic)

Data stores (Docker):  TimescaleDB :5432 (in use) · Redis :6379 (in use)
                       Qdrant :6333, Neo4j :7687, MinIO :9000 (provisioned for
                       Phases 2–3: RAG, knowledge graph, object storage)
```

Principles: hexagonal architecture — business logic depends on ports, vendors
live behind adapters, providers are swappable via env config
(`ARCTURUS_MARKET_DATA_PROVIDER`, `ARCTURUS_FUNDAMENTAL_DATA_PROVIDER`,
`ARCTURUS_NEWS_PROVIDER`). All prices are `Decimal`. All caching fails open.

## External calls (complete list)

| # | Destination | Made by | Trigger | Cached |
|---|---|---|---|---|
| 1 | Yahoo Finance (via `yfinance`) — quotes | `yahoo/adapter.py` | `GET /api/v1/market/quote/{symbol}` | Redis 30s |
| 2 | Yahoo Finance — OHLCV history | `yahoo/adapter.py` | `GET /api/v1/market/candles/{symbol}` | Redis 5m (default window) |
| 3 | Yahoo Finance — company info (`Ticker.info`) | `yahoo/adapter.py` | `GET /api/v1/market/profile/{symbol}`, `/fundamentals/{symbol}` | Redis 1h |
| 4 | Yahoo Finance — news feed (`Ticker.get_news`) | `yahoo/adapter.py` | `GET /api/v1/market/news/{symbol}` | Redis 5m |
| 5 | Arbitrary news-publisher pages (httpx GET, 8s timeout, 3MB cap, SSRF-guarded to public http/https only) | `trafilatura_reader.py` | `GET /api/v1/market/news/article?url=` | Redis 24h |
| 6 | Publisher image CDNs (news thumbnails / hero images) | browser `<img>` tags | rendering Workspace news | browser cache |
| 7 | NSE archives — `EQUITY_L.csv` (all NSE-listed equities) | `directories/adapters.py` | `POST /api/v1/instruments/sync` (manual/on-demand only) | persisted to DB |
| 8 | Nasdaq Trader symbol directory — `nasdaqlisted.txt`, `otherlisted.txt` (NASDAQ/NYSE/AMEX) | `directories/adapters.py` | `POST /api/v1/instruments/sync` (manual/on-demand only) | persisted to DB |

No other outbound calls exist. No telemetry, no third-party analytics. All
external data is delayed/unofficial (Yahoo) — not for latency-sensitive trading.

## API surface

```
GET  /health                              liveness
GET  /health/ready                        readiness (probes TimescaleDB)
GET  /api/v1/market/quote/{symbol}        symbols are EXCHANGE:TICKER, e.g. NSE:RELIANCE;
                                          indices use INDEX:^NSEI, INDEX:^GSPC, …
GET  /api/v1/market/movers                top gainers/losers (curated NIFTY-50 + US majors)
GET  /api/v1/market/indicators/{symbol}?interval=1d&specs=ema:20,rsi:14
                                          deterministic indicators (sma/ema/rsi/macd/bollinger/atr)
GET  /api/v1/strategies                   registered strategy plugins + metadata
GET  /api/v1/strategies/evaluate/{symbol} run all strategies -> explainable verdicts
                                          (stance/confidence/entry/stop/reasons)
GET  /api/v1/strategies/backtest/{symbol}?strategy=key
                                          3y prefix-replay backtest with costs (ADR-007)
GET  /api/v1/market/candles/{symbol}?interval=1d
GET  /api/v1/market/profile/{symbol}
GET  /api/v1/market/fundamentals/{symbol}
GET  /api/v1/market/news/{symbol}?limit=10
GET  /api/v1/market/news/article?url=     in-app reader-mode extraction
GET  /api/v1/instruments?query=&exchange=&limit=&offset=   browse/search all listed stocks
POST /api/v1/instruments/sync             refresh universe from official exchange listings
GET/POST        /api/v1/watchlists
GET/DELETE      /api/v1/watchlists/{id}
POST            /api/v1/watchlists/{id}/items
DELETE          /api/v1/watchlists/{id}/items/{symbol}
```

## Development workflow

The blueprint directory is the single source of truth:

- [PROJECT_VISION.md](AI_Trading_OS_Blueprint/PROJECT_VISION.md) — what we're building and why
- [SYSTEM_ARCHITECTURE.md](AI_Trading_OS_Blueprint/SYSTEM_ARCHITECTURE.md) — master architecture
- [ROADMAP.md](AI_Trading_OS_Blueprint/ROADMAP.md) — phases and milestones
- [TASKS.md](AI_Trading_OS_Blueprint/TASKS.md) — current work items
- [DECISIONS.md](AI_Trading_OS_Blueprint/DECISIONS.md) — architecture decision records
- [PROGRESS.md](AI_Trading_OS_Blueprint/PROGRESS.md) — status after every completed task

Quality gates (all must pass; CI runs them on every push):
`ruff check` · `ruff format --check` · `mypy --strict` · `pytest` ·
`eslint` · `next build`
