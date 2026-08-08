"""Backtest use cases: replay a strategy over ~3 years of daily history.

Every fresh computation (cache miss) is recorded in the Experiment Registry
(ADR-008) so any result can later be traced to the exact run that produced it.
Recording fails open: registry trouble never breaks a backtest response.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from arcturus_api.application.cache import CachePort
from arcturus_api.application.market.service import MarketDataService, _CachedService
from arcturus_api.domain.backtest.engine import ENGINE_VERSION, run_backtest
from arcturus_api.domain.backtest.models import BacktestConfig, BacktestResult
from arcturus_api.domain.market.models import Interval
from arcturus_api.domain.research.ports import ExperimentRepository
from arcturus_api.domain.strategy.models import UnknownStrategyError
from arcturus_api.domain.strategy.plugins import ALL_STRATEGIES

logger = logging.getLogger(__name__)

BACKTEST_TTL = 3600
_LOOKBACK_DAYS = 365 * 3


def _metrics_of(result: BacktestResult) -> dict[str, float | int | None]:
    return {
        "trade_count": len(result.trades),
        "total_return_pct": result.total_return_pct,
        "buy_hold_return_pct": result.buy_hold_return_pct,
        "win_rate_pct": result.win_rate_pct,
        "average_win_pct": result.average_win_pct,
        "average_loss_pct": result.average_loss_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "exposure_pct": result.exposure_pct,
        "annualized_sharpe": result.annualized_sharpe,
        "annualized_sortino": result.annualized_sortino,
        "calmar": result.calmar,
        "profit_factor": result.profit_factor,
        "expectancy_pct": result.expectancy_pct,
    }


class BacktestService(_CachedService):
    def __init__(
        self,
        market: MarketDataService,
        cache: CachePort | None = None,
        experiments: ExperimentRepository | None = None,
    ) -> None:
        super().__init__(cache)
        self._market = market
        self._experiments = experiments
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
            result = await asyncio.to_thread(run_backtest, strategy, candles, BacktestConfig())
            await self._record(result)
            return result

        return await self._cached(
            f"backtest:v2:{strategy_key}:{raw_symbol.upper()}",
            BACKTEST_TTL,
            BacktestResult,
            load,
        )

    async def _record(self, result: BacktestResult) -> None:
        if self._experiments is None:
            return
        try:
            await self._experiments.record(
                strategy_key=result.strategy.key,
                strategy_version=result.strategy.version,
                symbol=str(result.symbol),
                interval="1d",
                start=result.start,
                end=result.end,
                bars=result.bars,
                config=result.config.model_dump(),
                metrics=_metrics_of(result),
                engine_version=ENGINE_VERSION,
                validation=result.validation,
            )
        except Exception:
            logger.warning("experiment recording failed (fail-open)", exc_info=True)
