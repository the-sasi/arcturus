from datetime import UTC, datetime
from decimal import Decimal

from arcturus_api.application.market.service import MarketDataService
from arcturus_api.domain.market.models import CandleSeries, Interval, Quote, Symbol
from arcturus_api.domain.market.ports import MarketDataProvider


class DictCache:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.store[key] = value


class CountingProvider(MarketDataProvider):
    name = "counting"

    def __init__(self) -> None:
        self.quote_calls = 0

    async def get_quote(self, symbol: Symbol) -> Quote:
        self.quote_calls += 1
        return Quote(symbol=symbol, price=Decimal("100"), as_of=datetime.now(UTC))

    async def get_candles(
        self, symbol: Symbol, interval: Interval, start: datetime, end: datetime
    ) -> CandleSeries:
        return CandleSeries(symbol=symbol, interval=interval, candles=[])


class TestQuoteCaching:
    async def test_second_call_hits_cache(self) -> None:
        provider = CountingProvider()
        service = MarketDataService(provider, cache=DictCache())

        first = await service.get_quote("NSE:TCS")
        second = await service.get_quote("NSE:TCS")

        assert provider.quote_calls == 1
        assert first.price == second.price

    async def test_different_symbols_are_distinct_keys(self) -> None:
        provider = CountingProvider()
        service = MarketDataService(provider, cache=DictCache())

        await service.get_quote("NSE:TCS")
        await service.get_quote("NSE:INFY")

        assert provider.quote_calls == 2

    async def test_no_cache_still_works(self) -> None:
        provider = CountingProvider()
        service = MarketDataService(provider)

        await service.get_quote("NSE:TCS")
        await service.get_quote("NSE:TCS")

        assert provider.quote_calls == 2
