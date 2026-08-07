# Arcturus — AI Trading Operating System

An AI-first Decision Intelligence Platform for traders. Not a bot, not a signal
service — a complete trading workspace where every recommendation is explainable,
reproducible, evidence-based, and auditable.

> LLMs reason. Deterministic tools calculate.

## Repository layout

```
apps/web                  Next.js frontend (TypeScript, Tailwind, ShadCN)
services/api              FastAPI backend — modular monolith, clean architecture
infra/                    Docker Compose stack, deployment config
AI_Trading_OS_Blueprint/  Living specification: vision, roadmap, tasks, ADRs
```

## Quick start

Prerequisites: Docker, Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 22+.

```bash
# 1. Infrastructure (TimescaleDB, Redis, Qdrant, Neo4j, MinIO)
cd infra
cp .env.example .env
docker compose up -d

# 2. Backend API  → http://localhost:8600/docs
#    (port 8600 — 8000 is taken by another app on the dev machine;
#     keep NEXT_PUBLIC_API_URL in apps/web/.env.local in sync)
cd ../services/api
uv sync
uv run uvicorn arcturus_api.main:app --reload --port 8600

# 3. Frontend     → http://localhost:3000
cd ../../apps/web
npm install
npm run dev
```

## Development workflow

The blueprint directory is the single source of truth:

- [PROJECT_VISION.md](AI_Trading_OS_Blueprint/PROJECT_VISION.md) — what we're building and why
- [SYSTEM_ARCHITECTURE.md](AI_Trading_OS_Blueprint/SYSTEM_ARCHITECTURE.md) — master architecture
- [ROADMAP.md](AI_Trading_OS_Blueprint/ROADMAP.md) — phases and milestones
- [TASKS.md](AI_Trading_OS_Blueprint/TASKS.md) — current work items
- [DECISIONS.md](AI_Trading_OS_Blueprint/DECISIONS.md) — architecture decision records
- [PROGRESS.md](AI_Trading_OS_Blueprint/PROGRESS.md) — status after every completed task
