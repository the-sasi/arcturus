# Agent Platform + Investing — Phase 0 Architecture Audit

Date: 2026-09-15. Source directive: "Arcturus — Master Engineering & Agent
Implementation Prompt" (user, 2026-09-15).
Status: **PROPOSED — awaiting approval.** ADR-009 requires stop-and-ask before
the architecture expands; nothing below is accepted and no code has changed.

Verified baseline (run, not read from docs) at `4acb3f5`:
`ruff check` clean · `ruff format --check` clean · `mypy --strict` clean
(71 source files) · `pytest` 103 passed.

---

## 1. Current architecture (verified in code)

| Layer | What exists |
|---|---|
| API (`api/v1`) | health, market (quote/candles/profile/fundamentals/news/article/movers/regime/indicators), instruments, strategies (list/evaluate/backtest), research (experiments), watchlists. Composition root in `api/deps.py` + `main.py` lifespan. |
| Application | `MarketDataService`, `ResearchDataService` (both on `_CachedService` read-through Redis cache, fail-open), `IndicatorService`, `RegimeService`, `StrategyService` (regime-gated verdicts), `BacktestService` (records experiments), `WatchlistService`, `InstrumentDirectoryService`. |
| Domain | Pydantic frozen models throughout. Ports (ABC): `MarketDataProvider`, `FundamentalDataProvider`, `NewsProvider`, `ArticleReader`, `InstrumentDirectoryProvider`, `InstrumentRepository`, `WatchlistRepository`, `ExperimentRepository`; `CachePort` (Protocol). Pure modules: indicators (SMA/EMA/RSI/MACD/Bollinger/ATR), regime, strategy plugins (3), prefix-replay backtest engine v1.1.0. |
| Infrastructure | Yahoo (yfinance, thread-offloaded), trafilatura reader (8s timeout, 3MB cap, SSRF guard), NSE + Nasdaq Trader directories (httpx with timeouts), Redis cache (1s socket timeouts), SQLAlchemy async repos, Alembic 0001–0003. |
| Data stores | TimescaleDB + Redis in use. Qdrant/Neo4j/MinIO dormant (ADR-009). |
| Frontend | Next.js 16: Dashboard, Market Intelligence, Stock Workspace (chart, strategy panel, backtest panel, news reader), Watchlists. "AI Copilot" and "Portfolio Intelligence" are disabled sidebar stubs. |
| Agent layer | **None.** Zero LangGraph/LangChain/LangSmith/LLM-SDK code or dependencies (grep over `services/`). |
| Investing domain | **None.** No mutual funds, portfolios, holdings, transactions, goals, SIP or allocation code. |
| Users/auth | **None.** Single-user system; no user or session identity. |

## 2. Reusable components → directive tool mapping

Status key: **EXISTS** (wrap as-is) · **GAP** (small deterministic addition) ·
**MISSING** (new deterministic service) · **DATA** (blocked on a data source).

| Directive tool | Backed by | Status / notes |
|---|---|---|
| `get_quote` | `MarketDataService.get_quote` | EXISTS (30s cache) |
| `get_ohlcv` | `MarketDataService.get_candles` | EXISTS (5m cache for default window) |
| `get_index_data` | quote/candles on `INDEX:^NSEI` etc. | EXISTS via symbol convention |
| `get_market_regime` | `RegimeService.get_regime` | EXISTS — single rule (200-DMA + 50-DMA slope) |
| `get_market_movers` | `MarketDataService.get_movers` | EXISTS — **curated 50-symbol universe only** |
| `get_market_breadth` | `MoversSnapshot.advancing/declining` | EXISTS — same 50 symbols; not real exchange breadth |
| `search_instruments` | `InstrumentDirectoryService` | EXISTS — no sector data in the universe (sector only per-symbol via Yahoo profile) |
| `get_company_profile` | `ResearchDataService.get_profile` | EXISTS (1h cache) |
| `get_fundamentals` | `ResearchDataService.get_fundamentals` | EXISTS — 15 typed fields + extras (growth, margins, target price, recommendation). **No ROCE, no cash-flow, no statements, no history.** |
| `get_company_news` | `ResearchDataService.get_news` | EXISTS — Yahoo only |
| `get_article` | `ResearchDataService.read_article` | EXISTS — untrusted text; prompt-injection surface |
| `calculate_indicators` | `IndicatorService.compute` | EXISTS — **ATR is in the library but not in the spec grammar** |
| `calculate_returns` (1D…5Y) | — | GAP — pure function over candles |
| `calculate_volatility` | — | GAP — pure function over candles |
| `calculate_drawdown` | `backtest/engine._max_drawdown` (private) | GAP — extract to a shared pure module |
| `list_strategies` / `evaluate_strategy` | `StrategyService` | EXISTS — evaluate runs all 3 strategies, regime-gated |
| `backtest_strategy` | `BacktestService.backtest` | EXISTS — fixed 3y window + default config; `validation="in-sample-only"`. It is the only backtest an agent may cite as reproducible. TradingView imports (planned) may be cited only as `external-unverified` evidence (RESEARCH_PLATFORM_PLAN.md §5). |
| `get_experiments` | `ExperimentRepository` | EXISTS |
| `compare_strategies` | R3-lite leaderboard | MISSING (already NOW in TASKS) |
| `validate_data_quality` | R2 | MISSING (already NOW in TASKS) |
| `calculate_position_size` | — | MISSING (already NEXT) |
| `calculate_portfolio_risk` / concentration / stress test | — | MISSING — no portfolio domain |
| `calculate_asset_allocation` / `calculate_sip` / `construct_portfolio` / `calculate_rebalancing` | — | MISSING — no investing domain |
| `analyze_overlap` / `get_fund_holdings` | — | DATA — no holdings source |
| `search_mutual_funds` / `get_fund_profile` / `get_nav_history` / `get_fund_performance` / `get_fund_risk` | — | DATA — BACKLOG.md records "we do not cover mutual funds" |

Reusable patterns for the agent layer: `_CachedService`, provider registry,
plugin registry (`ALL_STRATEGIES`), domain error types already mapped to HTTP
codes, experiment-row JSONB provenance pattern, lifespan wiring, pure-function
modules with golden tests, scripted strategy doubles in tests.

## 3. Missing components

**Agent layer (all of it):** graph state and contracts, tool registry/gateway,
authorization, prompt registry and versioning, model abstraction + fake model,
audit events, tracing, request/correlation IDs (no middleware exists),
streaming endpoint, copilot UI, eval datasets.

**Deterministic prerequisites the agents would need:** data quality engine
(R2), returns/volatility/drawdown analytics, ATR exposure, leaderboard
(R3-lite), position sizing, outbound timeouts on Yahoo calls.

**Investing (entire mode):** mutual-fund domain + provider, NAV analytics
(CAGR, rolling returns, volatility, drawdown), SIP/XIRR math, allocation math,
portfolio/holding/transaction persistence, concentration and overlap
analytics, investor profile storage.

## 4. Conflicts and discrepancies

### A. Directive vs. governing decisions

1. **ADR-009 / RESEARCH_PLATFORM_PLAN §2 / TASKS.md** classify agent tooling
   (registry, gateway, evaluation) as **NOT NEEDED YET**. The directive's
   Phase 1 builds exactly that. Proceeding needs explicit approval and an
   ADR-010 that amends ADR-009.
2. **ADR-009 "nothing LATER while a NOW is open"**: R2 Data Quality Engine and
   R3-lite are open. The directive agrees on R2 — §25 puts it first in the
   research queue and §26 says "Implement the Data Quality Engine before
   trusting agent research."
3. **README "No telemetry, no third-party analytics"** vs. LangSmith (§22),
   which ships prompts, tool inputs/outputs and model responses to an
   external SaaS. Investing prompts would carry capital, goals and existing
   assets. It is a new row in the external-calls table and a privacy decision.
4. **New dependencies** (`langgraph`, `langchain-core`, an LLM SDK,
   `langsmith`) expand the architecture → stop-and-ask per ADR-009.
5. **ADR-009 "two real cases justify an abstraction"** vs. a mutual-fund
   provider port with no provider chosen, nine specialists, and a multi-level
   permission model when only READ_ONLY tools can exist.
6. **ROADMAP.md Phase 2** lists "LangGraph Supervisor + first specialist
   agents (Technical, Risk, Explanation)" while ADR-009 defers agents —
   the roadmap contradicts its own governing ADR.
7. **Product identity**: README, PROJECT_VISION and sidebar say "AI Trading
   OS … for traders"; the directive adds a co-equal Investing mode.
   PROJECT_VISION and README would need updating.
8. **AI_ARCHITECTURE.md** lists Technical/News/Macro/Risk/Psychology/Portfolio/
   Strategy/Historical agents — a different roster from the directive's nine.

### B. Directive's "existing foundation" vs. code

1. Movers and breadth cover a hand-picked 50 symbols (40 NSE + 10 US), not the
   market.
2. Fundamentals lack ROCE, cash flow, statement history; single Yahoo snapshot.
3. ATR exists in `domain/indicators/library.py` but `IndicatorService` only
   accepts `sma|ema|rsi|bollinger|macd`.
4. Position sizing, signal markers and data quality are not built.
5. Returns by window, volatility, support/resistance: no deterministic code.
6. **Decimal**: market-domain prices are `Decimal`, but indicators, strategy
   internals, `MarketRegime` values, `BacktestConfig.cost_per_side_pct`, and
   `BacktestTrade.entry_price/exit_price` are `float`. Acceptable for
   ratios/indicators; investing money amounts (capital, SIP, allocations)
   must be `Decimal` from day one.
7. **Typing looseness the directive forbids**: `validation: str` and
   `exit_reason: str` (should be enums); `ExperimentRepository.record(start:
   Any, end: Any)`; `metrics/config: dict[str, Any]`; `# type: ignore` at
   `domain/backtest/engine.py:155` and `application/market/service.py:138`;
   ruff ignores `ANN401`. Small, but agent contracts must not copy these.
8. **No timeout on Yahoo calls**: quote/candles/info/news run in
   `asyncio.to_thread` with no deadline, so a hung Yahoo call hangs the
   request. (Directories and article reader do have timeouts.) Note:
   `asyncio.wait_for` around `to_thread` abandons the thread rather than
   killing it, so the real fix is also a bounded executor.
9. No users/sessions: the directive's per-user caching, user/session trace
   metadata, and credential protections have nothing to attach to yet.
   Acceptable while single-user, but personalized outputs must never use
   shared cache keys.

### C. Documentation drift (housekeeping)

1. PROGRESS.md header still says "Current Status: Phase 1 Foundation — in
   progress"; ROADMAP marks Phase 1 "IN PROGRESS". Phase 2/2R are active.
2. TASKS.md Phase 1 "Remaining" lists three items that are done: GitHub push
   (`origin` = `git@github.com:the-sasi/arcturus.git`), Redis quote caching
   (`QUOTE_TTL = 30`), instruments table (migration 0002). "Redis readiness
   probe" is genuinely open — `/health/ready` probes only the database.
3. RESEARCH_PLATFORM_PLAN says R2 makes backtests **and strategy evaluation**
   refuse INVALID data; TASKS.md says only the backtester. Needs one answer.
4. ADR-009 is dated 2026-08-09 in DECISIONS.md; it was committed 2026-08-16.
5. CODING_STANDARDS.md says Black; the repo uses `ruff format`.
6. `docker-compose.yml` passes Qdrant/Neo4j URLs to the api and `Settings`
   carries MinIO/Neo4j credentials for infrastructure no code uses.

## 5. Risks

| Risk | Why it matters here | Mitigation |
|---|---|---|
| Fluent narration of bad data | No data quality engine; one bad Yahoo bar becomes a confident paragraph | R2 before agents; DQ status is a mandatory field on market evidence |
| In-sample results presented as edge | Every backtest is `in-sample-only` | `validation` carried verbatim into Evidence; eval test fails if dropped or paraphrased |
| Hallucinated numbers | LLM restating tool outputs | Final answer numbers must trace to a `tool_call_id`; eval checks every number against tool outputs |
| Prompt injection | We already fetch arbitrary publisher pages | Article/news text delimited as data; no write tools exist to hijack; injection fixtures in evals |
| Latency | User's standing requirement ("system should be fast"). A trading analysis fans out ~8 tool calls + several model calls; cold movers ≈6s, cold backtests are O(n²) × 3 strategies | Parallel tool calls, existing Redis caches, streaming progress, per-request latency budget, small graphs for simple asks |
| Hung threads | yfinance has no timeout | Adapter timeouts + bounded executor before the gateway relies on them |
| Token cost | No budget or metering today | Record usage per run; model tiering (small model for classification) |
| Data egress | LangSmith would receive investor financial details | Opt-in, redaction, off in CI; or local audit only |
| Over-building | 9 specialists × prompts × evals is a large surface for one user; directive §51 warns | Ship one vertical slice; split nodes into agents only when evals show a need |
| Regulatory (investing) | Personalized investment advice to others is regulated in India (SEBI adviser rules) — verify | Personal-use framing and decision-support disclaimers; revisit before any multi-user use |
| Data licensing | Yahoo is unofficial; Breeze feeds are per-account and non-redistributable | Unchanged from BACKLOG constraints |

## 6. Proposed implementation plan (NOW / NEXT / LATER)

### Step A — deterministic prerequisites · NOW · no new dependencies
- A1. **R2 Data Quality Engine** (already NOW): OHLC sanity, duplicates,
  gaps, staleness, impossible prices, timestamp order → VALID/WARNING/INVALID;
  backtester rejects INVALID; status recorded on experiments.
- A2. **Yahoo adapter timeouts** + bounded thread executor.
- A3. **Pure analytics module**: returns by window (1D…5Y), annualized
  volatility, max drawdown (extracted from the engine, one source of truth);
  expose ATR in the indicator grammar.
- A4. **R3-lite leaderboard** (already NOW).

### Step B — agent foundation · needs approval (ADR-010)
- Package `arcturus_api/agents/` **inside the existing monolith** — no new
  service, no new datastore.
- Strict Pydantic contracts (`extra="forbid"`, enums, `Decimal` money):
  `ResearchRequest`, `ResearchPlan`, `ToolCallRequest/Result`, `Evidence`
  (`FACT | INFERENCE | RECOMMENDATION`, source, timestamp, tool_call_id,
  data-quality status), `FinalAnswer`, `ErrorState`, `AuditEvent`.
- **Tool gateway** wrapping the existing application services from §2:
  READ_ONLY only; registering a non-read tool is rejected and tested. Each
  tool declares input/output schema, timeout, retry policy (retry only
  `ProviderUnavailableError`, bounded), and determinism flag. Every call
  emits an audit event.
- Prompts as versioned markdown files under `agents/prompts/` with a loader
  that records a content hash per run.
- Model behind a Protocol with a deterministic fake; CI never needs an API key.
- Audit persistence: structured log events first; an `agent_runs` JSONB table
  (same pattern as `experiments`) only if approved — see decision 6.
- Request-ID middleware (benefits the whole API, not just agents).

### Step C — first vertical slice · after B
"Analyse `<symbol>` for trading", end to end:

```
Supervisor (classify + plan)
  → research node   [quote, candles+DQ, returns, indicators, regime,
                     profile, fundamentals, news]          (parallel)
  → strategy node   [evaluate, backtest, experiments]
  → risk node       [deterministic checks: stop distance, ATR, regime,
                     DQ status; position sizing once built]
  → devil's advocate
  → consensus → FinalAnswer (conclusion, evidence, confidence, risks,
                             invalidation, unresolved questions)
```

- `POST /api/v1/ai/research` with SSE execution events. No clash with the
  existing `/api/v1/research/experiments` routes.
- Copilot page in the web app (sidebar stub already exists) showing progress,
  evidence, findings, and a Data/Analysis/Recommendation/Risk/Uncertainty split.
- Eval set with fake model + fake tools: tool selection, no fabricated
  numbers, `in-sample-only` preserved, tool failure → "Data unavailable",
  injection fixtures, no write-tool access.
- Specialists begin as graph nodes with scoped tool allowlists and prompts.
  Market Intelligence and Stock Research become separate agents only when the
  "best opportunities this week" workflow needs them.

### Step D — investing · LATER until its deterministic core and data exist
- D1. Data source decision (NAV history + scheme metadata are publicly
  available from AMFI; holdings, TER and AUM coverage from free sources is
  uncertain — verify before committing).
- D2. Deterministic core: mutual-fund domain, NAV analytics, SIP/XIRR,
  allocation math, portfolio/holding/transaction tables, concentration;
  overlap only once holdings data exists.
- D3. Then Investor Profile, Mutual Fund Research, and Portfolio agents on the
  same gateway.

### Not built in this plan
Nine agents on day one · Qdrant/Neo4j code paths · long-term memory ·
broker execution or any write tool · autonomous strategy work · multi-user
auth · LangSmith evaluation dashboards (Phase 6).

## 7. Decisions needed before any code

1. **Sequence** — Step A (R2 + small analytics + timeouts) before the agent
   foundation? *Recommended: yes* (ADR-009 NOW list; directive §26).
2. **Approve the agent layer now** — record ADR-010 amending ADR-009's
   "agent tooling NOT NEEDED YET"?
3. **LLM provider and model** — none is configured today.
4. **LangSmith** — opt-in SaaS tracing with redaction (external-calls row
   added), or local structured audit only for now?
5. **Investing scope** — accept that mutual funds are LATER behind a data
   source decision, and that overlap/sector exposure stay blocked until a
   holdings source exists?
6. **Agent audit persistence** — structured logs only, or one `agent_runs`
   table for provenance/replay?
