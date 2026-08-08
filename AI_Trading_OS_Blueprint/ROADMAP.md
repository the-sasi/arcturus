# Roadmap

## Phase 1: Foundation (IN PROGRESS — started 2026-08-07)

Goal: a runnable monorepo skeleton with enterprise-grade structure that every later
phase builds on without redesign.

- M1.1 — Repo + monorepo layout, blueprint docs wired into workflow
- M1.2 — Backend skeleton: FastAPI, clean architecture layers (domain / application /
  infrastructure / api), typed settings, health endpoints
- M1.3 — First hexagonal port: MarketDataProvider + Yahoo adapter (quotes + OHLCV)
- M1.4 — Infrastructure stack: Docker Compose (TimescaleDB, Redis, Qdrant, Neo4j, MinIO)
- M1.5 — Frontend skeleton: Next.js + TypeScript + Tailwind, app shell with module navigation
- M1.6 — Backend test harness (pytest) + CI-ready lint/typecheck config
- M1.7 — Persistence layer: SQLAlchemy + Alembic migrations, first domain tables

## Phase 2: Decision Engine

- Strategy Engine plugin framework (deterministic, versioned strategies)
- Indicator library (deterministic calculations, never in LLM prompts)
- Market Intelligence Tier 1 (see BACKLOG.md): movers, sector heatmap,
  screeners, index & breadth — deterministic, feeds off existing data
- Decision Engine: multi-factor evaluation producing explainable recommendations
- LangGraph Supervisor + first specialist agents (Technical, Risk, Explanation)

## Phase 3: Research

- News Intelligence pipeline + first RAG pipeline (news)
- Knowledge Graph (Neo4j) ingestion: companies, sectors, events
- Research Lab UI + Stock Workspace with TradingView charts
- Memory subsystem (session, conversation, research memories)

## Phase 4: Automation

- Alerts engine, scheduled research jobs (background workers)
- Paper trading + portfolio tracking
- Broker adapter ports (Upstox, Zerodha) — execution always behind risk validation,
  never LLM-initiated

## Phase 5: Production

- AuthN/AuthZ, multi-user tenancy groundwork
- Observability (structured logging, metrics, tracing)
- GitHub Actions CI/CD, Nginx, Kubernetes readiness
- Hardening, backups, rate limiting
