"""Provider registry — runtime adapter selection by name.

New providers register a factory here; selection is configuration
(``ARCTURUS_MARKET_DATA_PROVIDER``), never a code change in business logic.
"""

from collections.abc import Callable

from arcturus_api.domain.market.errors import UnknownProviderError
from arcturus_api.domain.market.ports import MarketDataProvider
from arcturus_api.infrastructure.providers.yahoo.adapter import YahooMarketDataProvider

_FACTORIES: dict[str, Callable[[], MarketDataProvider]] = {
    "yahoo": YahooMarketDataProvider,
}


def available_providers() -> list[str]:
    return sorted(_FACTORIES)


def create_market_data_provider(name: str) -> MarketDataProvider:
    factory = _FACTORIES.get(name.lower())
    if factory is None:
        raise UnknownProviderError(name, available_providers())
    return factory()
