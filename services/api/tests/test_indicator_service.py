from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from arcturus_api.application.market.indicator_service import IndicatorService
from arcturus_api.application.market.service import MarketDataService
from arcturus_api.domain.indicators.models import UnknownIndicatorError
from arcturus_api.domain.market.models import Candle, CandleSeries, Interval, Quote, Symbol
from arcturus_api.domain.market.ports import MarketDataProvider


class RampProvider(MarketDataProvider):
    """Serves a deterministic rising close series 1..40."""

    name = "ramp"

    async def get_quote(self, symbol: Symbol) -> Quote:
        raise NotImplementedError

    async def get_candles(
        self, symbol: Symbol, interval: Interval, start: datetime, end: datetime
    ) -> CandleSeries:
        base = datetime(2026, 1, 1, tzinfo=UTC)
        candles = [
            Candle(
                timestamp=base + timedelta(days=index),
                open=Decimal(index + 1),
                high=Decimal(index + 1),
                low=Decimal(index + 1),
                close=Decimal(index + 1),
                volume=1000,
            )
            for index in range(40)
        ]
        return CandleSeries(symbol=symbol, interval=interval, candles=candles)


@pytest.fixture
def service() -> IndicatorService:
    return IndicatorService(MarketDataService(RampProvider()))


class TestIndicatorService:
    async def test_computes_aligned_series(self, service: IndicatorService) -> None:
        result = await service.compute("NSE:TCS", Interval.DAY_1, ["sma:3", "rsi:14"])
        assert len(result.timestamps) == 40
        assert set(result.series) == {"sma_3", "rsi_14"}
        assert result.series["sma_3"][2] == 2.0
        assert result.series["rsi_14"][14] == 100.0  # monotonic ramp

    async def test_macd_and_bollinger_names(self, service: IndicatorService) -> None:
        result = await service.compute("NSE:TCS", Interval.DAY_1, ["macd", "bollinger:20"])
        assert {
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_upper_20",
            "bb_middle_20",
            "bb_lower_20",
        } == set(result.series)

    async def test_unknown_spec_raises(self, service: IndicatorService) -> None:
        with pytest.raises(UnknownIndicatorError):
            await service.compute("NSE:TCS", Interval.DAY_1, ["vwap:14"])

    async def test_out_of_range_period_raises(self, service: IndicatorService) -> None:
        with pytest.raises(UnknownIndicatorError):
            await service.compute("NSE:TCS", Interval.DAY_1, ["sma:501"])
