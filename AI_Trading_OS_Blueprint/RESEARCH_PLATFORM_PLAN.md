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

## 2. Implementation phases (incremental; each passes all gates + updates docs)

- **R1 — Experiment Registry + full fitness metrics** (NOW): every backtest
  computation persisted with strategy version, config, dataset window, engine
  version, metrics. Endpoints: list/get experiments. Metrics: + Sortino,
  Calmar, profit factor, expectancy.
- **R2 — Data Quality Engine**: deterministic candle validation
  (OHLC sanity, gaps, duplicates, staleness) → VALID/WARNING/INVALID; backtests
  and strategy evaluation refuse INVALID input; quality noted on experiments.
- **R3 — Strategy Registry v2**: DB-backed registry (status lifecycle
  PROPOSED→…→APPROVED, champion/challenger slots, mode RESEARCH/PAPER/SHADOW/LIVE
  flags); strategies compared across versions without overwriting history.
- **R4 — Validation ladder**: in-sample/out-of-sample split, rolling
  walk-forward, cross-symbol robustness sweep, parameter-stability probe;
  anti-overfitting report attached to experiments.
- **R5 — Degradation monitor + research scheduler**: rolling-window fitness vs
  baseline, DEGRADED flags, nightly data-quality / weekly health jobs
  (isolated worker, never touches execution).
- **R6 — Improvement Proposals workflow**: proposal objects (id, hypothesis,
  baseline, experiment refs, status lifecycle) + approve/reject endpoints —
  human approval as a hard gate.
- **R7 — Decision Memory**: record every evaluated opportunity + attach
  outcomes (needs paper/shadow execution from Phase 4 to close the loop).
- **R8 — Research UI workspace**: registry, experiment lab, health,
  proposals; RESEARCH/PAPER/SHADOW/LIVE visually distinct.
- **R9 — Discovery engine v1**: parameter search + feature-combination search
  over the validation ladder (programmatic, not LLM-invented).
- **Phase 3 gate — Tool Registry + Gateway** before ANY agent ships: agents
  reach tools only through authorization/validation/rate-limit/audit;
  default READ_ONLY.

## 3. Risks

- **Overfitting theater**: metrics without the R4 ladder can bless junk;
  until R4 lands, experiment records carry `validation: "in-sample-only"`.
- **Scope creep**: Qdrant/Neo4j/agents stay dormant until their inputs exist.
- **Data volume**: experiments are small JSON rows; Timescale is fine.
- **Safety**: no execution plane exists yet — the boundary list in ADR-008
  is recorded now so it predates any live-trading code.
