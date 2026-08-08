FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependency layer (cached until the lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN uv sync --locked --no-dev

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD \
  /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# Apply migrations, then serve
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn arcturus_api.main:app --host 0.0.0.0 --port 8000"]
