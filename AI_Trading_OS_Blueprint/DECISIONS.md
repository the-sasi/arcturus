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

## ADR-002: Qdrant as initial vector store (Accepted, 2026-08-07)

**Context.** Blueprint allows Milvus or Qdrant. Vector access will go through a
`VectorStorePort` regardless, so the engine is swappable by design.

**Decision.** Start with Qdrant: single lightweight container, first-class filtering,
simple API, production-capable. Milvus's multi-container footprint (etcd + MinIO +
pulsar) is unjustified at this stage.

**Consequences.** Smaller local stack. If scale later demands Milvus, only a new
adapter behind `VectorStorePort` is required — zero domain changes.

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
