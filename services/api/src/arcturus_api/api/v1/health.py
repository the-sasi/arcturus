"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from arcturus_api import __version__
from arcturus_api.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/health/ready")
async def ready(request: Request, response: Response) -> dict[str, str]:
    settings = get_settings()
    components: dict[str, str] = {}

    engine: AsyncEngine = request.app.state.db_engine
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        components["database"] = "up"
    except Exception:
        components["database"] = "down"

    degraded = any(state != "up" for state in components.values())
    if degraded:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "degraded" if degraded else "ready",
        "environment": settings.environment,
        **components,
    }
