"""FastAPI dependency wiring — the composition root.

This is the only place where concrete adapters meet application services.
"""

from functools import lru_cache

from fastapi import Request

from arcturus_api.application.identity.service import EntityResolutionService
from arcturus_api.application.market.directory_service import InstrumentDirectoryService
from arcturus_api.application.market.indicator_service import IndicatorService
from arcturus_api.application.market.regime_service import RegimeService
from arcturus_api.application.market.service import MarketDataService, ResearchDataService
from arcturus_api.application.quality.service import DataQualityService
from arcturus_api.application.strategy.backtest_service import BacktestService
from arcturus_api.application.strategy.service import StrategyService
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


@lru_cache
def get_indicator_service() -> IndicatorService:
    return IndicatorService(get_market_service())


@lru_cache
def get_regime_service() -> RegimeService:
    return RegimeService(get_market_service(), cache=get_cache())


@lru_cache
def get_strategy_service() -> StrategyService:
    return StrategyService(get_market_service(), regime=get_regime_service())


def get_backtest_service(request: Request) -> BacktestService:
    # Built in the app lifespan so it can record experiments (needs the DB)
    service: BacktestService = request.app.state.backtest_service
    return service


def get_identity_service(request: Request) -> EntityResolutionService:
    service: EntityResolutionService = request.app.state.identity_service
    return service


@lru_cache
def get_quality_service() -> DataQualityService:
    return DataQualityService(get_market_service())
