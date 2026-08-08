"""Market data endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from arcturus_api.api.deps import get_market_service, get_research_service
from arcturus_api.application.market.service import MarketDataService, ResearchDataService
from arcturus_api.domain.market.errors import (
    ArticleFetchError,
    ProviderUnavailableError,
    SymbolNotFoundError,
)
from arcturus_api.domain.market.fundamentals import (
    ArticleContent,
    CompanyProfile,
    Fundamentals,
    NewsArticle,
)
from arcturus_api.domain.market.models import CandleSeries, Interval, Quote

router = APIRouter(prefix="/market", tags=["market"])

MarketService = Annotated[MarketDataService, Depends(get_market_service)]
ResearchService = Annotated[ResearchDataService, Depends(get_research_service)]


@router.get("/quote/{symbol}")
async def get_quote(symbol: str, service: MarketService) -> Quote:
    """Latest quote. Symbol format: ``EXCHANGE:TICKER`` (e.g. ``NSE:RELIANCE``, ``NASDAQ:AAPL``)."""
    try:
        return await service.get_quote(symbol)
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/profile/{symbol}")
async def get_profile(symbol: str, service: ResearchService) -> CompanyProfile:
    """Company profile: sector, industry, description, headcount."""
    try:
        return await service.get_profile(symbol)
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/fundamentals/{symbol}")
async def get_fundamentals(symbol: str, service: ResearchService) -> Fundamentals:
    """Valuation and financial metrics: P/E, market cap, margins, 52-week range."""
    try:
        return await service.get_fundamentals(symbol)
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/news/article")
async def read_news_article(
    url: Annotated[str, Query(min_length=10, max_length=2000)],
    service: ResearchService,
) -> ArticleContent:
    """Reader-mode extraction of an article page, for in-app display."""
    try:
        return await service.read_article(url)
    except ArticleFetchError as exc:
        blocked = ("unsupported scheme", "missing host", "blocked host", "non-public address")
        status = 400 if exc.reason in blocked else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/news/{symbol}")
async def get_news(
    symbol: str,
    service: ResearchService,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[NewsArticle]:
    """Recent news for the instrument, newest first."""
    try:
        return await service.get_news(symbol, limit)
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
