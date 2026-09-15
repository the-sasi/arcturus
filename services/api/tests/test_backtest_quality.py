"""Trading consumes shared data safely: quality gate, provenance, and no lookahead."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from arcturus_api.application.market.service import MarketDataService
from arcturus_api.application.strategy.backtest_service import BacktestService
from arcturus_api.domain.backtest.engine import run_backtest
from arcturus_api.domain.data.sources import get_source
from arcturus_api.domain.market.models import Candle, CandleSeries, Interval, Quote, Symbol
from arcturus_api.domain.market.ports import MarketDataProvider
from arcturus_api.domain.quality.models import DataQualityError, DataQualityReport, QualityStatus
from arcturus_api.domain.research.models import Experiment
from arcturus_api.domain.research.ports import ExperimentRepository
from arcturus_api.domain.strategy.base import Strategy
from arcturus_api.domain.strategy.models import Stance, StrategyMetadata, StrategyVerdict


def fresh_candles(count: int) -> list[Candle]:
    last = datetime.now(UTC) - timedelta(hours=1)
    candles: list[Candle] = []
    for index in range(count):
        close = Decimal(100 + index % 9 + index // 10)
        candles.append(
            Candle(
                timestamp=last - timedelta(days=count - 1 - index),
                open=close - 1,
                high=close + 2,
                low=close - 3,
                close=close,
                volume=1000 + index * 10,
            )
        )
    return candles


class StaticYahoo(MarketDataProvider):
    name = "yahoo"

    def __init__(self, candles: list[Candle]) -> None:
        self._candles = candles

    async def get_quote(self, symbol: Symbol) -> Quote:
        raise NotImplementedError

    async def get_candles(
        self, symbol: Symbol, interval: Interval, start: datetime, end: datetime
    ) -> CandleSeries:
        return CandleSeries(symbol=symbol, interval=interval, candles=self._candles)


class RecordingExperiments(ExperimentRepository):
    def __init__(self) -> None:
        self.recorded: list[DataQualityReport | None] = []

    async def record(
        self,
        *,
        strategy_key: str,
        strategy_version: str,
        symbol: str,
        interval: str,
        start: Any,
        end: Any,
        bars: int,
        config: dict[str, Any],
        metrics: dict[str, Any],
        engine_version: str,
        validation: str,
        data_quality: DataQualityReport | None = None,
    ) -> Experiment:
        self.recorded.append(data_quality)
        return Experiment(
            id=uuid4(),
            strategy_key=strategy_key,
            strategy_version=strategy_version,
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
            bars=bars,
            config=config,
            metrics=metrics,
            engine_version=engine_version,
            validation=validation,
            data_quality=data_quality,
            created_at=datetime.now(UTC),
        )

    async def list(
        self, strategy_key: str | None, symbol: str | None, limit: int, offset: int
    ) -> tuple[list[Experiment], int]:
        raise NotImplementedError

    async def get(self, experiment_id: UUID) -> Experiment:
        raise NotImplementedError


def backtest_service(candles: list[Candle], experiments: RecordingExperiments) -> BacktestService:
    return BacktestService(MarketDataService(StaticYahoo(candles)), experiments=experiments)


class TestQualityGate:
    async def test_invalid_candles_are_refused_and_never_recorded(self) -> None:
        candles = fresh_candles(120)
        broken = candles[50]
        candles[50] = broken.model_copy(update={"high": broken.low - 1})
        experiments = RecordingExperiments()
        with pytest.raises(DataQualityError, match="high below low"):
            await backtest_service(candles, experiments).backtest("NSE:TEST", "range_breakout")
        assert experiments.recorded == []

    async def test_result_and_experiment_carry_traceable_quality(self) -> None:
        experiments = RecordingExperiments()
        result = await backtest_service(fresh_candles(120), experiments).backtest(
            "NSE:TEST", "range_breakout"
        )
        assert result.data_quality is not None
        assert result.data_quality.status == QualityStatus.VALID
        assert result.data_quality.source_id is not None
        assert get_source(result.data_quality.source_id).enabled  # traceable to a live source
        assert experiments.recorded == [result.data_quality]


class PrefixRecorder(Strategy):
    metadata = StrategyMetadata(
        key="recorder",
        name="Recorder",
        version="1.0.0",
        style="test",
        description="records what it can see",
        typical_holding="n/a",
    )
    min_candles = 5

    def __init__(self) -> None:
        self.seen: list[datetime] = []

    def evaluate(self, candles: CandleSeries) -> StrategyVerdict:
        self.seen.append(candles.candles[-1].timestamp)
        return StrategyVerdict(
            strategy=self.metadata,
            symbol=candles.symbol,
            stance=Stance.BULLISH,
            confidence=80,
            reasons=["test"],
            as_of=candles.candles[-1].timestamp,
        )


class TestPointInTime:
    def test_strategy_never_sees_a_bar_after_the_simulated_day(self) -> None:
        candles = fresh_candles(30)
        series = CandleSeries(
            symbol=Symbol.parse("NSE:TEST"), interval=Interval.DAY_1, candles=candles
        )
        strategy = PrefixRecorder()
        run_backtest(strategy, series)
        # Evaluation k sees exactly the history up to simulated day k — never later bars
        expected = [candle.timestamp for candle in candles[strategy.min_candles :]]
        assert strategy.seen == expected
