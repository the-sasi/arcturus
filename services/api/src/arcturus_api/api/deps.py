"""FastAPI dependency wiring — the composition root.

This is the only place where concrete adapters meet application services.
"""

from functools import lru_cache

from arcturus_api.application.market.service import MarketDataService
from arcturus_api.core.config import get_settings
from arcturus_api.infrastructure.providers.registry import create_market_data_provider


@lru_cache
def get_market_service() -> MarketDataService:
    settings = get_settings()
    provider = create_market_data_provider(settings.market_data_provider)
    return MarketDataService(provider)
