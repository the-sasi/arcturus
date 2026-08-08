"""Golden scenario tests: synthetic price histories with known correct verdicts."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from arcturus_api.domain.indicators.library import rsi
from arcturus_api.domain.market.models import Candle, CandleSeries, Interval, Symbol
from arcturus_api.domain.strategy.models import Stance
from arcturus_api.domain.strategy.plugins import (
    EmaCrossoverStrategy,
    RangeBreakoutStrategy,
    RsiMeanReversionStrategy,
)


def build_series(
    closes: list[float],
    volumes: list[int] | None = None,
    last_high: float | None = None,
    last_low: float | None = None,
) -> CandleSeries:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    volumes = volumes or [10_000] * len(closes)
    candles = []
    for index, close in enumerate(closes):
        is_last = index == len(closes) - 1
        high = last_high if is_last and last_high is not None else close * 1.01
        low = last_low if is_last and last_low is not None else close * 0.99
        candles.append(
            Candle(
                timestamp=base + timedelta(days=index),
                open=Decimal(str(round(close, 2))),
                high=Decimal(str(round(high, 2))),
                low=Decimal(str(round(low, 2))),
                close=Decimal(str(round(close, 2))),
                volume=volumes[index],
            )
        )
    return CandleSeries(symbol=Symbol.parse("NSE:TEST"), interval=Interval.DAY_1, candles=candles)


class TestEmaCrossover:
    def test_downtrend_then_strong_rally_is_bullish(self) -> None:
        closes = [120 - 20 * (i / 60) for i in range(60)] + [100 + 30 * (i / 30) for i in range(30)]
        verdict = EmaCrossoverStrategy().evaluate(build_series(closes))
        assert verdict.stance == Stance.BULLISH
        assert verdict.confidence >= 50
        assert verdict.entry_zone is not None
        assert verdict.stop_loss is not None
        assert any("EMA20" in reason for reason in verdict.reasons)

    def test_downtrend_is_bearish(self) -> None:
        closes = [100 + 10 * (i / 40) for i in range(40)] + [110 - 30 * (i / 50) for i in range(50)]
        verdict = EmaCrossoverStrategy().evaluate(build_series(closes))
        assert verdict.stance == Stance.BEARISH
        assert verdict.entry_zone is None  # only bullish setups carry entries for now

    def test_flat_market_is_neutral(self) -> None:
        verdict = EmaCrossoverStrategy().evaluate(build_series([100.0] * 80))
        assert verdict.stance == Stance.NEUTRAL


class TestRsiMeanReversion:
    def test_dip_in_uptrend_is_bullish(self) -> None:
        rising = [100 + 100 * (i / 110) for i in range(112)]
        dip = [rising[-1] - 3.5 * (i + 1) for i in range(9)]
        closes = rising + dip
        series = build_series(closes)
        assert (value := rsi([float(c.close) for c in series.candles], 14)[-1]) is not None
        assert value < 35  # sanity: the scenario really is oversold
        verdict = RsiMeanReversionStrategy().evaluate(series)
        assert verdict.stance == Stance.BULLISH
        assert verdict.stop_loss is not None

    def test_oversold_in_downtrend_has_no_edge(self) -> None:
        falling = [200 - 100 * (i / 110) for i in range(112)]
        dip = [falling[-1] - 3 * (i + 1) for i in range(9)]
        verdict = RsiMeanReversionStrategy().evaluate(build_series(falling + dip))
        assert verdict.stance == Stance.NEUTRAL
        assert any("downtrend" in reason for reason in verdict.reasons)

    def test_flat_market_is_neutral(self) -> None:
        verdict = RsiMeanReversionStrategy().evaluate(build_series([100.0] * 130))
        assert verdict.stance == Stance.NEUTRAL


class TestRangeBreakout:
    def test_breakout_on_volume_is_bullish(self) -> None:
        closes = [95 + (i % 5) for i in range(39)] + [104.0]
        volumes = [10_000] * 39 + [30_000]
        verdict = RangeBreakoutStrategy().evaluate(
            build_series(closes, volumes, last_high=105.0, last_low=100.0)
        )
        assert verdict.stance == Stance.BULLISH
        assert verdict.confidence >= 55
        assert verdict.stop_loss is not None
        assert any("Volume confirms" in reason for reason in verdict.reasons)

    def test_breakout_without_volume_is_unconfirmed(self) -> None:
        closes = [95 + (i % 5) for i in range(39)] + [104.0]
        verdict = RangeBreakoutStrategy().evaluate(
            build_series(closes, last_high=105.0, last_low=100.0)
        )
        assert verdict.stance == Stance.NEUTRAL
        assert any("unconfirmed" in reason for reason in verdict.reasons)

    def test_breakdown_is_bearish(self) -> None:
        closes = [100 + (i % 5) for i in range(39)] + [92.0]
        volumes = [10_000] * 39 + [25_000]
        verdict = RangeBreakoutStrategy().evaluate(
            build_series(closes, volumes, last_high=95.0, last_low=91.0)
        )
        assert verdict.stance == Stance.BEARISH
