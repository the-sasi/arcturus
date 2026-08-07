"""Hexagonal ports for market data.

Business logic depends only on these interfaces — never on a vendor SDK.
Swapping Yahoo for Polygon/Upstox/Bloomberg means writing a new adapter; the
domain and application layers do not change.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from arcturus_api.domain.market.models import CandleSeries, Interval, Quote, Symbol


class MarketDataProvider(ABC):
    """Port for market quote and historical candle retrieval."""

    name: str

    @abstractmethod
    async def get_quote(self, symbol: Symbol) -> Quote:
        """Return the latest quote. Raises SymbolNotFoundError if unknown."""

    @abstractmethod
    async def get_candles(
        self,
        symbol: Symbol,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> CandleSeries:
        """Return historical OHLCV candles for [start, end]."""
