"""FastAPI dependency wiring — the composition root.

This is the only place where concrete adapters meet application services.
"""

from functools import lru_cache

from fastapi import Request

from arcturus_api.application.market.directory_service import InstrumentDirectoryService
from arcturus_api.application.market.service import MarketDataService, ResearchDataService
from arcturus_api.application.watchlist.service import WatchlistService
from arcturus_api.core.config import get_settings
from arcturus_api.infrastructure.cache.redis_cache import RedisCache
from arcturus_api.infrastructure.providers.registry import (
    create_fundamental_data_provider,
    create_market_data_provider,
    create_news_provider,
)
from arcturus_api.infrastructure.readers.trafilatura_reader import TrafilaturaArticleReader


@lru_cache
def get_cache() -> RedisCache:
    return RedisCache(get_settings().redis_url)


@lru_cache
def get_market_service() -> MarketDataService:
    settings = get_settings()
    provider = create_market_data_provider(settings.market_data_provider)
    return MarketDataService(provider, cache=get_cache())


@lru_cache
def get_research_service() -> ResearchDataService:
    settings = get_settings()
    return ResearchDataService(
        fundamentals=create_fundamental_data_provider(settings.fundamental_data_provider),
        news=create_news_provider(settings.news_provider),
        reader=TrafilaturaArticleReader(),
        cache=get_cache(),
    )


def get_watchlist_service(request: Request) -> WatchlistService:
    # Session factory is created once in the app lifespan (main.py).
    service: WatchlistService = request.app.state.watchlist_service
    return service


def get_directory_service(request: Request) -> InstrumentDirectoryService:
    service: InstrumentDirectoryService = request.app.state.directory_service
    return service
