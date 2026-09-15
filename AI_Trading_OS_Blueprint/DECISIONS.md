# Architecture Decisions

Format: lightweight ADRs, newest last. Status: Proposed | Accepted | Superseded.

---

## ADR-001: Monorepo layout (Accepted, 2026-08-07)

**Context.** The platform spans a Next.js frontend, a Python backend, and shared
infrastructure config. The blueprint requires modular services that can later split
into microservices.

**Decision.** Single repo at `arcturus/` with:

```
apps/web              # Next.js frontend
services/api          # FastAPI backend (modular monolith, service-splittable)
infra/                # docker-compose, nginx, deployment config
AI_Trading_OS_Blueprint/  # living specification & planning docs
```

**Consequences.** One clone, one CI pipeline, atomic cross-cutting changes. Backend is
a modular monolith whose modules (`market`, `strategy`, `decision`, …) each own their
domain and can be extracted into services later without domain changes.

---

## ADR-002: Qdrant as initial vector store (Superseded by ADR-009, 2026-08-09)

**Context.** Blueprint allows Milvus or Qdrant. Vector access will go through a
`VectorStorePort` regardless, so the engine is swappable by design.

**Decision.** Start with Qdrant: single lightweight container, first-class filtering,
simple API, production-capable. Milvus's multi-container footprint (etcd + MinIO +
pulsar) is unjustified at this stage.

**Consequences.** Smaller local stack. If scale later demands Milvus, only a new
adapter behind `VectorStorePort` is required — zero domain changes.

**Superseded (2026-08-09).** ADR-009 makes pgvector in the existing
PostgreSQL/TimescaleDB the first vector store: no second datastore is justified
before semantic search has a real, measured need. Qdrant remains an option only
if pgvector demonstrably fails at our scale.

---

## ADR-003: uv for Python dependency management (Accepted, 2026-08-07)

**Context.** uv 0.10 is installed; it provides lockfiles, fast resolution, and
`pyproject.toml`-native workflows.

**Decision.** `uv` with `pyproject.toml` + `uv.lock` for `services/api`.

**Consequences.** Reproducible envs, fast CI installs. Contributors need uv installed.

---

## ADR-004: npm for frontend package management (Accepted, 2026-08-07)

**Context.** pnpm is not installed on the dev machine; the frontend is a single app,
so workspace-level dedup benefits are minimal today.

**Decision.** npm with `package-lock.json`. Revisit pnpm if a JS package workspace
(shared UI kit, SDK) emerges.

---

## ADR-005: Async-first backend, yfinance behind a thread offload (Accepted, 2026-08-07)

**Context.** FastAPI is async; yfinance is synchronous.

**Decision.** All ports are `async` interfaces. Sync vendor SDKs (yfinance) are wrapped
with `asyncio.to_thread` inside their adapter. The domain and application layers never
see sync/async vendor differences.

**Consequences.** Uniform async contracts; swapping to a natively-async provider
(Polygon websockets, Upstox) changes only the adapter.

---

## ADR-006: Asset-class-agnostic instrument model from day one (Accepted, 2026-08-07)

**Context.** Blueprint mandates supporting equities, ETFs, options, futures, forex,
crypto, commodities without redesign.

**Decision.** Core domain model is `Instrument` with `AssetClass` enum, `Exchange`,
`currency`, and an extensible `attributes` mapping for class-specific fields (strike,
expiry, contract size). Symbols are namespaced `EXCHANGE:SYMBOL` internally; adapters
translate to vendor-specific tickers (e.g. `NSE:RELIANCE` → `RELIANCE.NS` for Yahoo).

**Consequences.** New asset classes are additive. Vendor symbol quirks are quarantined
in adapters.

---

## ADR-007: Custom prefix-replay backtester instead of OSS engines (Accepted, 2026-08-09)

**Context.** M2.2b needs backtesting. Candidates: `backtesting.py`, `vectorbt`, or
custom. Both OSS engines require strategies to be re-written in their own idioms
(their Strategy subclass / vectorized signal arrays) — duplicating every rule that
already lives in our plugin contract, creating two sources of truth per strategy.

**Decision.** A minimal in-domain replay engine: walk the candle history bar by bar,
call `strategy.evaluate(prefix)` exactly as production does, simulate entries at next
open, ATR-stop and stance-flip exits, percent costs per side. No-lookahead holds by
construction because the strategy only ever receives past candles.

**Consequences.** One source of truth: the deployed strategy IS the backtested
strategy. O(n²) replay is acceptable at daily frequency (~750 bars); results cached
in Redis. If Tier 2 needs vectorized speed (universe-wide scans), revisit vectorbt
as an *additional* fast path — never as the primary definition of a strategy.

**Amended (2026-09-15) — minimal internal engine + external integrations.**
Directive: *"Maintain a minimal deterministic internal backtesting capability
for reproducible agent-driven research, while supporting external backtesting
integrations such as TradingView where they provide superior functionality."*

- The internal engine stays **minimal**: it is the reproducible reference for
  the experiment registry and agent citations. It grows only when agent research
  needs a reproducible number it cannot produce. There is no feature parity with
  external strategy testers (UI, intrabar simulation, scripting, optimisers).
- **External engines** (TradingView first) are integrated for what they do
  better. Their results enter as user-provided imports:
  - the trade list is stored as an external fact
  - metrics are recomputed by Arcturus from those trades
  - provenance is recorded (platform, file hash, import time)
  - results are labelled `external-unverified`
- External results are never ranked with internal results. Agents cite them only
  as external evidence; claims of edge or validation require the internal engine.
- No public TradingView backtest API is assumed (VERIFY_REQUIRED); no scraping or
  UI automation.

Details: RESEARCH_PLATFORM_PLAN.md §5.

---

## ADR-008: Research plane & controlled self-improvement (Accepted, 2026-08-09)

**Context.** Arcturus is evolving into a quantitative research platform that
evaluates and improves its own strategies, tools, and data. Uncontrolled
self-modification in a trading system is unacceptable.

**Decision.**
1. Two planes: a RESEARCH plane (discovery, experiments, validation, registry)
   and a DECISION/EXECUTION plane. Research jobs are isolated from execution.
2. The only self-improvement path is: observation → evaluation → improvement
   proposal → experiment → validation → **human approval** → deployment.
   Statuses: PROPOSED / EXPERIMENT / VALIDATING / APPROVED / REJECTED / ROLLED_BACK.
3. Every research result is reproducible: experiments record strategy version,
   dataset window, config, engine version, and metrics (registry from R1 on).
4. LLMs (when they arrive, Phase 3) reason, summarize, hypothesize, and explain;
   deterministic code owns every number (P&L, risk, sizing, metrics). Agents
   reach tools only through a gateway (authz → schema validation → rate limit
   → audit), default READ_ONLY.
5. **Never self-modifiable**: risk limits, kill-switch behavior, broker
   credentials, user permissions, KYC/compliance rules, production deployment
   permissions, live-trading authorization. Safe self-healing is limited to
   infrastructure remedies (retries, cache refresh, reconnects, fallback
   providers, disabling failing research jobs) and every action is logged.

**Consequences.** Slower "autonomy" than naive agent designs, by design. The
phased plan lives in RESEARCH_PLATFORM_PLAN.md; each phase updates docs and
passes all quality gates.

---

## ADR-009: Build what matters — pragmatism over architecture (Accepted, 2026-08-09)

**Context.** Arcturus has accumulated provisioned-but-unused infrastructure
(Qdrant, Neo4j, MinIO containers with zero code paths) and a nine-phase research
wishlist (RESEARCH_PLATFORM_PLAN.md) written from an aspirational directive. The
risk is a beautifully layered system that never earns money or trust because
effort went to architecture instead of product value.

**Decision.** Every component, dependency, and abstraction must pass five
questions BEFORE it is built:

1. What concrete problem does it solve?
2. Is it needed **now**, or is it speculation?
3. Can the existing architecture already do it?
4. What measurable value does it add?
5. Is the added complexity justified?

If any answer is unclear: **do not implement it.**

Standing consequences of that rule:

- **Classification gate.** Every roadmap item is labelled NOW / NEXT / LATER /
  NOT NEEDED. Nothing labelled LATER is built while anything labelled NOW is
  incomplete.
- **Priority order** (higher wins when trading off): correctness → reliable
  market data → deterministic calculations → backtest correctness → strategy
  evaluation → risk controls → explainability → reproducibility →
  observability → UX → performance → advanced AI.
- **Defaults**: one modular service (no microservices) · one database
  (PostgreSQL/TimescaleDB; **pgvector before Qdrant**, **PG relations before
  Neo4j**) · deterministic code before LLMs · rules before ML · SQL before RAG ·
  the app's own mechanisms before a scheduler/worker tier · existing infra
  before new infra.
- **Stop and ask.** Any change that expands the architecture or adds an
  infrastructure dependency requires explicit human approval first — it is not
  an implementation detail.
- **No speculative abstractions**: no ports, plugin layers, or provider
  interfaces for a second implementation that does not exist yet. Two real
  cases justify an abstraction; one does not.

**Consequences.** RESEARCH_PLATFORM_PLAN.md is re-scoped under this ADR (see its
"Build-what-matters classification" section): R2 and R3-lite are NOW, the
validation ladder and degradation monitor are NEXT, and the discovery engine,
agent tooling, research scheduler, Qdrant/Neo4j code paths, and the full
proposal workflow are LATER or NOT NEEDED until real evidence demands them.
Dormant containers stay in compose (they cost nothing when stopped) but no code
may target them; the vector-search need, when it arrives, is served by pgvector
in the existing database. ADR-002 (Qdrant as initial vector store) is thereby
**superseded for the current phase** — revisit only if pgvector demonstrably
fails at our scale.
