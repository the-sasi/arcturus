"""Provider registry — runtime adapter selection by name.

New providers register a factory here; selection is configuration
(``ARCTURUS_MARKET_DATA_PROVIDER``), never a code change in business logic.
"""

from collections.abc import Callable
from typing import TypeVar

from arcturus_api.domain.market.errors import UnknownProviderError
from arcturus_api.domain.market.ports import (
    FundamentalDataProvider,
    MarketDataProvider,
    NewsProvider,
)
from arcturus_api.infrastructure.providers.yahoo.adapter import YahooMarketDataProvider

T = TypeVar("T")

_MARKET_FACTORIES: dict[str, Callable[[], MarketDataProvider]] = {
    "yahoo": YahooMarketDataProvider,
}
_FUNDAMENTAL_FACTORIES: dict[str, Callable[[], FundamentalDataProvider]] = {
    "yahoo": YahooMarketDataProvider,
}
_NEWS_FACTORIES: dict[str, Callable[[], NewsProvider]] = {
    "yahoo": YahooMarketDataProvider,
}


def available_providers() -> list[str]:
    return sorted(_MARKET_FACTORIES)


def _create(name: str, factories: dict[str, Callable[[], T]]) -> T:
    factory = factories.get(name.lower())
    if factory is None:
        raise UnknownProviderError(name, sorted(factories))
    return factory()


def create_market_data_provider(name: str) -> MarketDataProvider:
    return _create(name, _MARKET_FACTORIES)


def create_fundamental_data_provider(name: str) -> FundamentalDataProvider:
    return _create(name, _FUNDAMENTAL_FACTORIES)


def create_news_provider(name: str) -> NewsProvider:
    return _create(name, _NEWS_FACTORIES)
