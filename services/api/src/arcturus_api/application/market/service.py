"""Market data use cases.

Depends only on the MarketDataProvider port — never on a concrete adapter.
"""

from datetime import UTC, datetime, timedelta

from arcturus_api.domain.market.fundamentals import CompanyProfile, Fundamentals, NewsArticle
from arcturus_api.domain.market.models import CandleSeries, Interval, Quote, Symbol
from arcturus_api.domain.market.ports import (
    FundamentalDataProvider,
    MarketDataProvider,
    NewsProvider,
)

_DEFAULT_LOOKBACK: dict[Interval, timedelta] = {
    Interval.MIN_1: timedelta(days=1),
    Interval.MIN_5: timedelta(days=5),
    Interval.MIN_15: timedelta(days=5),
    Interval.MIN_30: timedelta(days=10),
    Interval.HOUR_1: timedelta(days=30),
    Interval.DAY_1: timedelta(days=365),
    Interval.WEEK_1: timedelta(days=365 * 3),
    Interval.MONTH_1: timedelta(days=365 * 10),
}


class MarketDataService:
    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def get_quote(self, raw_symbol: str) -> Quote:
        return await self._provider.get_quote(Symbol.parse(raw_symbol))

    async def get_candles(
        self,
        raw_symbol: str,
        interval: Interval = Interval.DAY_1,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> CandleSeries:
        resolved_end = end or datetime.now(UTC)
        resolved_start = start or resolved_end - _DEFAULT_LOOKBACK[interval]
        return await self._provider.get_candles(
            Symbol.parse(raw_symbol), interval, resolved_start, resolved_end
        )


class ResearchDataService:
    """Company profile, fundamentals, and news — each behind its own port."""

    def __init__(self, fundamentals: FundamentalDataProvider, news: NewsProvider) -> None:
        self._fundamentals = fundamentals
        self._news = news

    async def get_profile(self, raw_symbol: str) -> CompanyProfile:
        return await self._fundamentals.get_profile(Symbol.parse(raw_symbol))

    async def get_fundamentals(self, raw_symbol: str) -> Fundamentals:
        return await self._fundamentals.get_fundamentals(Symbol.parse(raw_symbol))

    async def get_news(self, raw_symbol: str, limit: int = 10) -> list[NewsArticle]:
        return await self._news.get_news(Symbol.parse(raw_symbol), limit)
