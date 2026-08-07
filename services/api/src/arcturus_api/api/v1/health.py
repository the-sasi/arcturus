"""Liveness and readiness endpoints."""

from fastapi import APIRouter

from arcturus_api import __version__
from arcturus_api.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    settings = get_settings()
    # Infrastructure probes (DB, Redis, …) attach here as those clients land (M1.7).
    return {"status": "ready", "environment": settings.environment}
