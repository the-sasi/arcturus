"""Market data endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from arcturus_api.api.deps import get_market_service
from arcturus_api.application.market.service import MarketDataService
from arcturus_api.domain.market.errors import (
    ProviderUnavailableError,
    SymbolNotFoundError,
)
from arcturus_api.domain.market.models import CandleSeries, Interval, Quote

router = APIRouter(prefix="/market", tags=["market"])

MarketService = Annotated[MarketDataService, Depends(get_market_service)]


@router.get("/quote/{symbol}")
async def get_quote(symbol: str, service: MarketService) -> Quote:
    """Latest quote. Symbol format: ``EXCHANGE:TICKER`` (e.g. ``NSE:RELIANCE``, ``NASDAQ:AAPL``)."""
    try:
        return await service.get_quote(symbol)
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    service: MarketService,
    interval: Interval = Interval.DAY_1,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
) -> CandleSeries:
    """Historical OHLCV candles. Defaults to a sensible lookback window per interval."""
    try:
        return await service.get_candles(symbol, interval, start, end)
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
