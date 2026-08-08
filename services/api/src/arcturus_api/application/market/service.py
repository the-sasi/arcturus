"""Market data use cases.

Depends only on ports — never on concrete adapters. Read paths cache vendor
responses (fail-open) so repeated requests don't pay vendor latency.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from arcturus_api.application.cache import CachePort, NullCache
from arcturus_api.domain.market.fundamentals import (
    ArticleContent,
    CompanyProfile,
    Fundamentals,
    NewsArticle,
)
from arcturus_api.domain.market.models import CandleSeries, Interval, Quote, Symbol
from arcturus_api.domain.market.ports import (
    ArticleReader,
    FundamentalDataProvider,
    MarketDataProvider,
    NewsProvider,
)

ModelT = TypeVar("ModelT", bound=BaseModel)

QUOTE_TTL = 30
CANDLES_TTL = 300
PROFILE_TTL = 3600
FUNDAMENTALS_TTL = 3600
NEWS_TTL = 300
ARTICLE_TTL = 86400

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


class _CachedService:
    def __init__(self, cache: CachePort | None) -> None:
        self._cache: CachePort = cache if cache is not None else NullCache()

    async def _cached(
        self,
        key: str,
        ttl: int,
        model: type[ModelT],
        load: Callable[[], Awaitable[ModelT]],
    ) -> ModelT:
        raw = await self._cache.get(key)
        if raw is not None:
            return model.model_validate_json(raw)
        value = await load()
        await self._cache.set(key, value.model_dump_json(), ttl)
        return value

    async def _cached_list(
        self,
        key: str,
        ttl: int,
        model: type[ModelT],
        load: Callable[[], Awaitable[list[ModelT]]],
    ) -> list[ModelT]:
        adapter: TypeAdapter[list[ModelT]] = TypeAdapter(list[model])  # type: ignore[valid-type]
        raw = await self._cache.get(key)
        if raw is not None:
            return adapter.validate_json(raw)
        value = await load()
        await self._cache.set(key, adapter.dump_json(value).decode(), ttl)
        return value


class MarketDataService(_CachedService):
    def __init__(self, provider: MarketDataProvider, cache: CachePort | None = None) -> None:
        super().__init__(cache)
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def get_quote(self, raw_symbol: str) -> Quote:
        symbol = Symbol.parse(raw_symbol)
        return await self._cached(
            f"quote:{symbol}", QUOTE_TTL, Quote, lambda: self._provider.get_quote(symbol)
        )

    async def get_candles(
        self,
        raw_symbol: str,
        interval: Interval = Interval.DAY_1,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> CandleSeries:
        symbol = Symbol.parse(raw_symbol)
        resolved_end = end or datetime.now(UTC)
        resolved_start = start or resolved_end - _DEFAULT_LOOKBACK[interval]

        def load() -> Awaitable[CandleSeries]:
            return self._provider.get_candles(symbol, interval, resolved_start, resolved_end)

        if start is None and end is None:
            # Default window is deterministic per (symbol, interval) — cacheable.
            return await self._cached(
                f"candles:{symbol}:{interval}", CANDLES_TTL, CandleSeries, load
            )
        return await load()


class ResearchDataService(_CachedService):
    """Company profile, fundamentals, news, and article reading — each behind a port."""

    def __init__(
        self,
        fundamentals: FundamentalDataProvider,
        news: NewsProvider,
        reader: ArticleReader,
        cache: CachePort | None = None,
    ) -> None:
        super().__init__(cache)
        self._fundamentals = fundamentals
        self._news = news
        self._reader = reader

    async def get_profile(self, raw_symbol: str) -> CompanyProfile:
        symbol = Symbol.parse(raw_symbol)
        return await self._cached(
            f"profile:{symbol}",
            PROFILE_TTL,
            CompanyProfile,
            lambda: self._fundamentals.get_profile(symbol),
        )

    async def get_fundamentals(self, raw_symbol: str) -> Fundamentals:
        symbol = Symbol.parse(raw_symbol)
        return await self._cached(
            f"fundamentals:{symbol}",
            FUNDAMENTALS_TTL,
            Fundamentals,
            lambda: self._fundamentals.get_fundamentals(symbol),
        )

    async def get_news(self, raw_symbol: str, limit: int = 10) -> list[NewsArticle]:
        symbol = Symbol.parse(raw_symbol)
        return await self._cached_list(
            f"news:{symbol}:{limit}",
            NEWS_TTL,
            NewsArticle,
            lambda: self._news.get_news(symbol, limit),
        )

    async def read_article(self, url: str) -> ArticleContent:
        return await self._cached(
            f"article:{url}", ARTICLE_TTL, ArticleContent, lambda: self._reader.read(url)
        )
