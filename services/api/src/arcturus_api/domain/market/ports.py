"""Hexagonal ports for market data.

Business logic depends only on these interfaces — never on a vendor SDK.
Swapping Yahoo for Polygon/Upstox/Bloomberg means writing a new adapter; the
domain and application layers do not change.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from arcturus_api.domain.market.fundamentals import (
    ArticleContent,
    CompanyProfile,
    Fundamentals,
    NewsArticle,
)
from arcturus_api.domain.market.models import (
    CandleSeries,
    Exchange,
    Instrument,
    Interval,
    Quote,
    Symbol,
)


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


class FundamentalDataProvider(ABC):
    """Port for company profile and fundamental metrics."""

    name: str

    @abstractmethod
    async def get_profile(self, symbol: Symbol) -> CompanyProfile:
        """Return the company profile. Raises SymbolNotFoundError if unknown."""

    @abstractmethod
    async def get_fundamentals(self, symbol: Symbol) -> Fundamentals:
        """Return fundamental metrics. Raises SymbolNotFoundError if unknown."""


class NewsProvider(ABC):
    """Port for instrument-related news."""

    name: str

    @abstractmethod
    async def get_news(self, symbol: Symbol, limit: int = 10) -> list[NewsArticle]:
        """Return recent news for the instrument, newest first."""


class ArticleReader(ABC):
    """Port for reader-mode extraction of an article page by URL."""

    name: str

    @abstractmethod
    async def read(self, url: str) -> ArticleContent:
        """Fetch and extract the article. Raises ArticleFetchError on failure."""


class InstrumentDirectoryProvider(ABC):
    """Port for fetching an exchange's official listing directory."""

    name: str
    source_id: str  # key in the data source registry (domain.data.sources)

    @abstractmethod
    async def fetch_listings(self) -> list[Instrument]:
        """Download and parse the full listing. Raises ProviderUnavailableError."""


class InstrumentRepository(ABC):
    """Port for the persisted instrument universe."""

    @abstractmethod
    async def search(
        self,
        query: str | None,
        exchange: Exchange | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Instrument], int]:
        """Return (matching instruments ordered by symbol, total match count)."""

    @abstractmethod
    async def upsert_many(self, instruments: list[Instrument]) -> int:
        """Insert or update by symbol; returns number written."""
