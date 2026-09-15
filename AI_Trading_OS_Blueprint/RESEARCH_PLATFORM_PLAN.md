# Research Platform Upgrade — Audit & Phased Plan

Date: 2026-08-09. Source directive: "Advanced Tooling, Self-Improvement & Quant
Research Upgrade" (user, 2026-08-09). Governing ADR: ADR-008.

## Target loop (canonical)

```
                 ARCTURUS
                     │
       ┌─────────────┴─────────────┐
       │                           │
   RESEARCH                    DECISION
       │                           │
 Strategy Discovery           Strategies
       │                           │
 Experiment                     Regime
       │                           │
 Validation                      Risk
       │                           │
 Strategy Registry             Decision
       │                           │
       └───────────┬───────────────┘
                   ▼
             OUTCOME DATA → SELF-EVALUATION → IMPROVEMENT PROPOSAL
                                → EXPERIMENT → VALIDATION → HUMAN APPROVAL
```

Self-improvement is evidence → proposal → experiment → validation → HUMAN
APPROVAL. Never LLM → code change → production. Safety boundary (§38 of the
directive) is absolute: risk limits, kill switches, broker credentials,
permissions, compliance rules are never self-modifiable.

## 1. Capability audit (directive § → status)

| Directive area | Status | Current implementation / gap |
|---|---|---|
| Hexagonal core, ports, Decimal, fail-open cache (§1) | EXISTS | domain/application/infrastructure layering; 8 ports; enforced by ADRs 001–007 |
| Strategy versioning (§5) | PARTIAL | `StrategyMetadata.version` exists; no persisted registry, status lifecycle, or A/B history |
| Strategy discovery (§6) | MISSING | No candidate-generation framework |
| Anti-overfitting ladder (§7) | PARTIAL | No-lookahead by construction (ADR-007) + costs; missing OOS split, walk-forward, cross-symbol/regime, robustness stages |
| Experiment registry (§8) | MISSING → **R1 (this increment)** | Backtests are cached, not recorded/reproducible |
| Strategy fitness (§9) | PARTIAL → **R1** | Have return/buy-hold/win-rate/avg-win-loss/maxDD/exposure/Sharpe; adding Sortino, Calmar, profit factor, expectancy; composite score later (versioned formula) |
| Degradation detection (§10) | MISSING | Needs rolling-window comparison vs baseline; depends on R1 history |
| Regime learning (§11) | PARTIAL | Rule-based regime + confidence gating shipped; per-regime strategy performance tracking missing |
| Tool registry/gateway/self-eval (§12–14) | MISSING | No agents exist yet; build as the mandatory front door BEFORE first agent ships (Phase 3 gate) |
| Data quality engine (§15–16) | MISSING | Yahoo data enters backtester unvalidated today |
| Decision memory + outcome learning (§17–18) | MISSING | Depends on paper/shadow modes |
| Agent evaluation (§19–21) | N/A yet | No agents in the codebase; specs recorded for Phase 3 |
| Research scheduler (§22) | MISSING | No job runner; candidates: lightweight APScheduler worker container |
| Baseline / champion–challenger / shadow (§23–25) | MISSING | Depends on registry (R3) + paper engine (Phase 4 precursor) |
| Safe self-healing (§26) | PARTIAL | Fail-open cache, provider fallback (NSE URL list), regime fail-open; no health flagging/logged actions registry |
| Qdrant research KB / Neo4j graph (§27–28) | PROVISIONED, UNUSED | Containers run; no code paths; deferred until content exists to store |
| Report generator, provenance, reproducibility (§29–31) | PARTIAL → R1 starts | Deterministic result objects exist (verdicts/backtests); experiment_id provenance starts in R1 |
| Research APIs (§32) | MISSING → **R1 adds first two** | `/api/v1/research/experiments[…]` |
| Research UI (§33) | MISSING | After R3 there is enough data to show |
| Alerts (§34) | MISSING | Needs degradation/data-quality signals first |
| Cost/perf awareness (§35–36) | PARTIAL | Redis hit ratios implicit; no metrics surface; defer until bottleneck evidence |
| Testing discipline (§37, §41) | EXISTS | 96 tests, golden scenarios, scripted doubles, all gates enforced |

Reusable building blocks: `_CachedService`, SQLAlchemy repo pattern +
Alembic, provider registry pattern, plugin registry pattern, pure-function
domain modules with fixture tests, app.state lifespan wiring.

## 2. Build-what-matters classification (ADR-009, 2026-08-09)

The nine-phase plan below was written from an aspirational directive. ADR-009
re-scopes it: each item must name the concrete problem it solves *today*.
**Nothing labelled LATER is built while anything labelled NOW is incomplete.**

| Item | Class | Problem it solves now / why deferred |
|---|---|---|
| R2 Data Quality Engine | **NOW** | Yahoo candles enter the backtester unvalidated. A single bad bar (zero volume, split artefact, stale close, duplicate date) silently produces a fake edge. Priority #2 and #4. Uses existing code paths — no new infra. |
| R3-lite Strategy comparison | **NOW** | We now record every backtest but cannot answer "which strategy/version actually works". A leaderboard query over the **existing** experiments table + one endpoint. No new tables, no lifecycle states. |
| R4 Validation ladder (OOS split → walk-forward) | **NEXT** | Every result today is `in-sample-only`; we must not trust a strategy without out-of-sample evidence. Deferred only behind R2 because validating dirty data is pointless. |
| Position sizing + chart signal markers (Phase 2 leftovers) | **NEXT** | Risk controls (#6) and explainability (#7); small, self-contained. |
| R3-full Strategy Registry (status lifecycle, champion/challenger, mode flags) | LATER | Needs multiple competing live versions and a paper engine to be meaningful. Premature state machine today. |
| R5 Degradation monitor | LATER | Requires a track record that does not exist yet. Rolling comparison against a baseline needs months of outcomes. |
| R6 Improvement-proposal workflow | LATER | Nothing generates proposals yet. ADR-008's human-approval gate is recorded; the object model waits for a real producer. |
| R7 Decision memory + outcome learning | LATER | Closes only when paper/shadow execution exists (Phase 4). |
| R8 Research UI | LATER (thin slice earlier) | Once R2+R3-lite produce data, a small panel in the existing Workspace suffices — not a separate research workspace. |
| R9 Discovery engine | LATER | Parameter search over an unvalidated ladder manufactures overfitting. Only after R4. |
| Research scheduler / worker container | **NOT NEEDED** | On-demand endpoints + manual sync already cover every current job. A scheduler tier is infra we would run for one nightly task. Revisit when a job must run unattended. |
| Qdrant code paths / research KB | **NOT NEEDED** | No content to embed, no semantic query in the product. When it arrives: **pgvector in the existing database** (ADR-009 supersedes ADR-002). |
| Neo4j knowledge graph | **NOT NEEDED** | Company/sector/event relations are a handful of PostgreSQL tables at our scale. |
| MinIO object storage | **NOT NEEDED** | Nothing produces artefacts too large for the DB. |
| Agent tooling: tool registry, gateway, agent evaluation (§12–14, §19–21) | **NOT NEEDED YET** | Zero agents exist. Specs stay recorded as the Phase 3 gate: no agent ships without the gateway — but neither is built until an agent has a job deterministic code cannot do. |
| Alerts engine (§34), cost/perf metrics surface (§35–36) | LATER | No signals to alert on yet; no measured bottleneck. |
| Internal backtest engine — minimal scope (see §5) | **NOW** (maintain) | The reproducible reference that the experiment registry and future agents cite. Grows only through the §5 growth rule. |
| External backtest import — TradingView first (see §5) | **NEXT** (after R3-lite and R4) | Uses TradingView's strengths without rebuilding them. Moves up if strategies are already being run in TradingView and need comparing/citing. |
| Internal engine feature parity with TradingView (strategy-tester UI, intrabar/tick simulation, scripting language, optimisers) | **NOT NEEDED** | External tools already do this better; duplicating them violates ADR-009. |

Dormant containers (Qdrant, Neo4j, MinIO) stay in `docker-compose.yml` for now —
they cost nothing while stopped — but **no code may target them**. Removing them
from compose is a separate, explicitly-approved change (ADR-009 stop-and-ask).

## 3. Phase definitions (as originally specified)

- **R1 ✔ Experiment Registry + full fitness metrics** (done 2026-08-09): every
  backtest persisted with strategy version, config, dataset window, engine
  version, metrics. Endpoints: list/get experiments.
- **R2 — Data Quality Engine** (NOW): deterministic candle validation
  (OHLC sanity, gaps, duplicates, staleness) → VALID/WARNING/INVALID; backtests
  and strategy evaluation refuse INVALID input; quality recorded on experiments.
- **R3 — Strategy comparison** (NOW, lite): leaderboard over experiment history;
  full registry with lifecycle states deferred.
- **R4 — Validation ladder** (NEXT): in-sample/out-of-sample split, then rolling
  walk-forward; cross-symbol robustness and parameter-stability probes follow.
  Results stop being labelled `in-sample-only` only when they earn it.
- **R5–R9** — see the classification table above for gating conditions.
- **Phase 3 gate — Tool Registry + Gateway** before ANY agent ships: agents reach
  tools only through authorization/validation/rate-limit/audit, default READ_ONLY.

## 4. Risks

- **Overfitting theater**: metrics without the R4 ladder can bless junk;
  until R4 lands, experiment records carry `validation: "in-sample-only"`.
- **External results mistaken for validated evidence**: TradingView numbers come
  from a different engine, feed, and fill model. Mitigation (§5.2):
  `external-unverified` label, metrics recomputed from imported trades, no
  leaderboard mixing, agents cite them only as external evidence.
- **Internal engine scope creep**: pressure to match TradingView features.
  Mitigation: the §5.1 growth rule.
- **Scope creep**: Qdrant/Neo4j/agents stay dormant until their inputs exist.
- **Data volume**: experiments are small JSON rows; Timescale is fine.
- **Safety**: no execution plane exists yet — the boundary list in ADR-008
  is recorded now so it predates any live-trading code.

## 5. Backtesting strategy: minimal internal engine + external integrations (2026-09-15)

> **Principle:** Maintain a minimal deterministic internal backtesting capability
> for reproducible agent-driven research, while supporting external backtesting
> integrations such as TradingView where they provide superior functionality.

Backtesting is Trading-owned (shared-platform boundary, ADR-011). Investing
portfolio simulation is a separate concern and is not covered here.

### 5.1 Internal engine — the reproducible reference

The prefix-replay engine (ADR-007) exists so that any number an agent or the
experiment registry cites can be re-run by Arcturus and give the same answer.

**In scope (keep or build):**
- Deterministic replay of the *registered* strategy plugins — the same code that
  produces live verdicts (one source of truth).
- Data quality gate on inputs (R2: INVALID candles are refused ✔).
- Point-in-time correctness: prefix replay today; point-in-time fundamentals
  and events once they enter the shared platform.
- A simple, explicit, versioned execution model: next-open fills, ATR stops,
  gap handling, per-side costs (`ENGINE_VERSION`).
- Experiment registry records: strategy version, data window, config, engine
  version, data quality report, metrics.
- R4 validation ladder (out-of-sample → walk-forward); position sizing once built.

**Out of scope (do not build):** strategy-tester UI parity, intrabar/tick or
bar-magnifier simulation, a strategy scripting language, parameter optimisers
or genetic search (R9 stays LATER), broker-grade order types, and multi-asset
portfolio backtesting.

**Growth rule:** the internal engine gains a capability only when
agent-driven research needs a *reproducible* number it cannot yet produce.
Anything needed only for human exploration belongs in an external tool.

### 5.2 External integrations — TradingView first

**Role:** human-facing exploration, plus features where external platforms are
better (Pine Script strategies, intrabar fill modelling, the indicator library,
visual trade markers).

**Access (VERIFY_REQUIRED):** no public TradingView API for running backtests or
retrieving Strategy Tester results is known — confirm before building. The
realistic mechanisms are:
- **Trade-list import:** the user exports Strategy Tester results and uploads
  the file (source type USER_PROVIDED).
- **Webhook alerts** (paid TradingView plans): *live signals*, not backtests.
  Out of scope for backtesting.
- No scraping or UI automation of TradingView, per the data-platform access rules.

**Import contract** (to be implemented as one Trading-owned slice):
- `ExternalBacktestResult`:
  - platform `tradingview`, plus the strategy name and version as the user reports them
  - symbol resolved through entity resolution
  - the external platform's price feed recorded as the data source — not ours
  - import provenance: file content hash, `imported_at`, uploader
  - the imported trade list is stored as the external *fact*
- **Metrics:** recomputed deterministically by Arcturus from the imported trades
  with the same metric code as the internal engine. The platform's own summary
  figures are kept alongside for comparison, never substituted.
- **Label:** `validation = "external-unverified"`. External results are never
  ranked in the internal leaderboard (R3-lite) — they are shown alongside it.
- **Registry:** a `tradingview` entry in the source registry with licence status
  UNKNOWN until the terms are reviewed.

**Reconciliation (optional):** when the same rules exist as an internal plugin,
run both over the same window. Record material metric differences as a
`DataConflict` (external vs internal engine) — never silently average or pick one.

**Agent rule:** an agent may cite an external backtest only as *external
evidence*, with platform and provenance. Claims of edge, robustness or
validation status require the internal engine.

### 5.3 Why this split

| Concern | Internal engine | External (TradingView) |
|---|---|---|
| Reproducible by Arcturus | Yes (versioned code + DQ-gated data) | No (black-box engine and feed) |
| Same code as live verdicts | Yes | No |
| Point-in-time / no-lookahead guarantee | By construction, tested | Platform-dependent; unverifiable |
| Rich exploration, intrabar fills, Pine ecosystem | Deliberately minimal | Strong |
| Suitable for agent citation | Yes | Only as labelled external evidence |
