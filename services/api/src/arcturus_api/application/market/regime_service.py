"""Market regime use cases."""

from arcturus_api.application.cache import CachePort
from arcturus_api.application.market.service import MarketDataService, _CachedService
from arcturus_api.domain.market.models import Exchange, Interval, Symbol
from arcturus_api.domain.market.regime import MarketRegime, compute_regime

REGIME_TTL = 1800

# Benchmark index per exchange — the market a stock actually swims in
_INDEX_BY_EXCHANGE: dict[Exchange, str] = {
    Exchange.NSE: "INDEX:^NSEI",
    Exchange.BSE: "INDEX:^BSESN",
    Exchange.NASDAQ: "INDEX:^GSPC",
    Exchange.NYSE: "INDEX:^GSPC",
    Exchange.AMEX: "INDEX:^GSPC",
}
_DEFAULT_INDEX = "INDEX:^GSPC"


class RegimeService(_CachedService):
    def __init__(self, market: MarketDataService, cache: CachePort | None = None) -> None:
        super().__init__(cache)
        self._market = market

    def index_for(self, exchange: Exchange) -> str:
        return _INDEX_BY_EXCHANGE.get(exchange, _DEFAULT_INDEX)

    async def get_regime(self, exchange: Exchange) -> MarketRegime:
        index_raw = self.index_for(exchange)

        async def load() -> MarketRegime:
            candles = await self._market.get_candles(index_raw, Interval.DAY_1)
            closes = [float(candle.close) for candle in candles.candles]
            return compute_regime(Symbol.parse(index_raw), closes, candles.candles[-1].timestamp)

        return await self._cached(f"regime:{index_raw}", REGIME_TTL, MarketRegime, load)
