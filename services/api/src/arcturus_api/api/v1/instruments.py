"""Instrument directory endpoints: browse/search the listed universe."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from arcturus_api.api.deps import get_directory_service
from arcturus_api.application.market.directory_service import InstrumentDirectoryService
from arcturus_api.domain.market.directory import DirectorySyncResult, InstrumentPage
from arcturus_api.domain.market.models import Exchange

router = APIRouter(prefix="/instruments", tags=["instruments"])

Service = Annotated[InstrumentDirectoryService, Depends(get_directory_service)]


@router.get("")
async def search_instruments(
    service: Service,
    query: Annotated[str | None, Query(max_length=100)] = None,
    exchange: Exchange | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InstrumentPage:
    """Browse or search all listed stocks (name or ticker, any exchange)."""
    return await service.search(query, exchange, limit, offset)


@router.post("/sync")
async def sync_instruments(service: Service) -> list[DirectorySyncResult]:
    """Refresh the universe from official exchange listings (NSE, Nasdaq Trader)."""
    return await service.sync_all()
