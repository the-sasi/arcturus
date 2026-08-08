"""Strategy plugin contract."""

from abc import ABC, abstractmethod

from arcturus_api.domain.market.models import CandleSeries
from arcturus_api.domain.strategy.models import StrategyMetadata, StrategyVerdict


class Strategy(ABC):
    """A deterministic, versioned trading strategy plugin.

    Implementations receive daily candle history and must be pure: same
    candles in, same verdict out. All indicator math comes from
    ``domain.indicators.library`` — never reimplemented inline.
    """

    metadata: StrategyMetadata
    min_candles: int

    @abstractmethod
    def evaluate(self, candles: CandleSeries) -> StrategyVerdict:
        """Produce a verdict. Raises InsufficientHistoryError if too little data."""
