"""Strategy evaluation use cases."""

import logging

from arcturus_api.application.market.service import MarketDataService
from arcturus_api.domain.market.models import Interval
from arcturus_api.domain.strategy.models import (
    InsufficientHistoryError,
    StrategyMetadata,
    StrategyVerdict,
)
from arcturus_api.domain.strategy.plugins import ALL_STRATEGIES

logger = logging.getLogger(__name__)


class StrategyService:
    def __init__(self, market: MarketDataService) -> None:
        self._market = market

    def list_strategies(self) -> list[StrategyMetadata]:
        return [strategy.metadata for strategy in ALL_STRATEGIES]

    async def evaluate_all(self, raw_symbol: str) -> list[StrategyVerdict]:
        """Run every registered strategy on daily candles; skip those lacking history."""
        candles = await self._market.get_candles(raw_symbol, Interval.DAY_1)
        verdicts: list[StrategyVerdict] = []
        for strategy in ALL_STRATEGIES:
            try:
                verdicts.append(strategy.evaluate(candles))
            except InsufficientHistoryError as exc:
                logger.info("skipping %s for %s: %s", strategy.metadata.key, raw_symbol, exc)
        return verdicts
