"""Data platform endpoints: source registry and recorded data conflicts."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from arcturus_api.api.deps import get_identity_service
from arcturus_api.application.identity.service import EntityResolutionService
from arcturus_api.domain.data.conflicts import DataConflictPage, ResolutionStatus
from arcturus_api.domain.data.sources import SOURCES, DataSource

router = APIRouter(prefix="/data", tags=["data"])

Identity = Annotated[EntityResolutionService, Depends(get_identity_service)]


@router.get("/sources")
async def list_sources() -> list[DataSource]:
    """Every registered source: authority tier, licence/access status, and whether
    it is actually implemented. Planned sources provide no data."""
    return list(SOURCES)


@router.get("/conflicts")
async def list_conflicts(
    service: Identity,
    status: ResolutionStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DataConflictPage:
    """Conflicting observations recorded by deterministic checks, newest first."""
    return await service.list_conflicts(status, limit, offset)
