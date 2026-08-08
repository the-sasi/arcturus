"""Backtest use cases: replay a strategy over ~3 years of daily history."""

import asyncio
from datetime import UTC, datetime, timedelta

from arcturus_api.application.cache import CachePort
from arcturus_api.application.market.service import MarketDataService, _CachedService
from arcturus_api.domain.backtest.engine import run_backtest
from arcturus_api.domain.backtest.models import BacktestConfig, BacktestResult
from arcturus_api.domain.market.models import Interval
from arcturus_api.domain.strategy.models import UnknownStrategyError
from arcturus_api.domain.strategy.plugins import ALL_STRATEGIES

BACKTEST_TTL = 3600
_LOOKBACK_DAYS = 365 * 3


class BacktestService(_CachedService):
    def __init__(self, market: MarketDataService, cache: CachePort | None = None) -> None:
        super().__init__(cache)
        self._market = market
        self._by_key = {strategy.metadata.key: strategy for strategy in ALL_STRATEGIES}

    async def backtest(self, raw_symbol: str, strategy_key: str) -> BacktestResult:
        strategy = self._by_key.get(strategy_key)
        if strategy is None:
            raise UnknownStrategyError(strategy_key, sorted(self._by_key))

        async def load() -> BacktestResult:
            end = datetime.now(UTC)
            candles = await self._market.get_candles(
                raw_symbol, Interval.DAY_1, start=end - timedelta(days=_LOOKBACK_DAYS), end=end
            )
            # CPU-bound prefix replay — keep it off the event loop
            return await asyncio.to_thread(run_backtest, strategy, candles, BacktestConfig())

        return await self._cached(
            f"backtest:v1:{strategy_key}:{raw_symbol.upper()}",
            BACKTEST_TTL,
            BacktestResult,
            load,
        )
