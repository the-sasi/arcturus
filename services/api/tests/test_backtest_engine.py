"""Backtest engine tests using a scripted strategy — trades are hand-checkable."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from arcturus_api.domain.backtest.engine import run_backtest
from arcturus_api.domain.backtest.models import BacktestConfig
from arcturus_api.domain.market.models import Candle, CandleSeries, Interval, Symbol
from arcturus_api.domain.strategy.base import Strategy
from arcturus_api.domain.strategy.models import (
    Stance,
    StrategyMetadata,
    StrategyVerdict,
)

ZERO_COST = BacktestConfig(cost_per_side_pct=0.0, entry_confidence=55)


def make_series(rows: list[tuple[float, float, float, float]]) -> CandleSeries:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [
        Candle(
            timestamp=base + timedelta(days=index),
            open=Decimal(str(row[0])),
            high=Decimal(str(row[1])),
            low=Decimal(str(row[2])),
            close=Decimal(str(row[3])),
            volume=1000,
        )
        for index, row in enumerate(rows)
    ]
    return CandleSeries(symbol=Symbol.parse("NSE:TEST"), interval=Interval.DAY_1, candles=candles)


class ScriptedStrategy(Strategy):
    """Emits pre-scripted verdicts keyed by bar index (len(prefix)-1)."""

    metadata = StrategyMetadata(
        key="scripted",
        name="Scripted",
        version="1.0.0",
        style="test",
        description="test double",
        typical_holding="n/a",
    )
    min_candles = 2

    def __init__(self, script: dict[int, tuple[Stance, int, float | None]]) -> None:
        self._script = script

    def evaluate(self, candles: CandleSeries) -> StrategyVerdict:
        bar = len(candles.candles) - 1
        stance, confidence, stop = self._script.get(bar, (Stance.NEUTRAL, 30, None))
        return StrategyVerdict(
            strategy=self.metadata,
            symbol=candles.symbol,
            stance=stance,
            confidence=confidence,
            entry_zone=None,
            stop_loss=None if stop is None else Decimal(str(stop)),
            reasons=["scripted"],
            as_of=candles.candles[-1].timestamp,
        )


FLAT = (100.0, 101.0, 99.0, 100.0)


class TestBacktestEngine:
    def test_profitable_trade_signal_flip_exit(self) -> None:
        # Bullish at bar 3 -> enter bar 4 open (100); neutral at bar 6 -> exit bar 7 open (120)
        rows = [
            FLAT,
            FLAT,
            FLAT,
            FLAT,
            (100, 112, 99, 110),
            (112, 116, 110, 115),
            (116, 121, 115, 120),
            (120, 122, 119, 121),
            FLAT,
            FLAT,
        ]
        script = {
            3: (Stance.BULLISH, 70, None),
            4: (Stance.BULLISH, 70, None),
            5: (Stance.BULLISH, 70, None),
            6: (Stance.NEUTRAL, 30, None),
        }
        result = run_backtest(ScriptedStrategy(script), make_series(rows), ZERO_COST)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.entry_price == 100.0
        assert trade.exit_price == 120.0
        assert trade.exit_reason == "signal_flip"
        assert trade.return_pct == 20.0
        assert result.total_return_pct == 20.0
        assert result.win_rate_pct == 100.0

    def test_stop_exit_and_gap_fill(self) -> None:
        # Enter at bar 4 open (100) with stop 95; bar 6 gaps to open 90 (below stop)
        rows = [
            FLAT,
            FLAT,
            FLAT,
            FLAT,
            (100, 101, 98, 99),
            (99, 100, 96, 97),
            (90, 92, 88, 91),
            FLAT,
            FLAT,
        ]
        script = {
            3: (Stance.BULLISH, 70, 95.0),
            4: (Stance.BULLISH, 70, 95.0),
            5: (Stance.BULLISH, 70, 95.0),
        }
        result = run_backtest(ScriptedStrategy(script), make_series(rows), ZERO_COST)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == "stop"
        assert trade.exit_price == 90.0  # gap through stop fills at the open, not at 95
        assert trade.return_pct == -10.0

    def test_no_signals_means_no_trades(self) -> None:
        result = run_backtest(ScriptedStrategy({}), make_series([FLAT] * 12), ZERO_COST)
        assert result.trades == []
        assert result.total_return_pct == 0.0
        assert result.win_rate_pct is None
        assert result.exposure_pct == 0.0

    def test_open_position_closed_at_end(self) -> None:
        rows = [FLAT, FLAT, FLAT, FLAT, (100, 111, 99, 110)]
        script = {3: (Stance.BULLISH, 70, None), 4: (Stance.BULLISH, 70, None)}
        result = run_backtest(ScriptedStrategy(script), make_series(rows), ZERO_COST)
        assert len(result.trades) == 1
        assert result.trades[0].exit_reason == "end_of_data"
        assert result.trades[0].return_pct == 10.0

    def test_costs_reduce_returns(self) -> None:
        rows = [
            FLAT,
            FLAT,
            FLAT,
            FLAT,
            (100, 112, 99, 110),
            (112, 116, 110, 115),
            (116, 121, 115, 120),
            (120, 122, 119, 121),
            FLAT,
            FLAT,
        ]
        script = {
            3: (Stance.BULLISH, 70, None),
            4: (Stance.BULLISH, 70, None),
            5: (Stance.BULLISH, 70, None),
            6: (Stance.NEUTRAL, 30, None),
        }
        costly = run_backtest(
            ScriptedStrategy(script),
            make_series(rows),
            BacktestConfig(cost_per_side_pct=0.5, entry_confidence=55),
        )
        assert costly.trades[0].return_pct < 20.0
        # entry 100*1.005, exit 120*0.995 -> ~18.8%
        assert 18.0 < costly.trades[0].return_pct < 19.0

    def test_low_confidence_bullish_ignored(self) -> None:
        rows = [FLAT] * 10
        script = {4: (Stance.BULLISH, 40, None)}  # below entry_confidence 55
        result = run_backtest(ScriptedStrategy(script), make_series(rows), ZERO_COST)
        assert result.trades == []

    def test_buy_hold_benchmark(self) -> None:
        rows = [FLAT, FLAT, (100, 101, 99, 100)] + [(110, 111, 109, 110)] * 3
        result = run_backtest(ScriptedStrategy({}), make_series(rows), ZERO_COST)
        assert result.buy_hold_return_pct == 10.0
