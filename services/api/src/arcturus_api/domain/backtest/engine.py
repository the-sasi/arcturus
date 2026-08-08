"""Prefix-replay backtest engine.

Each simulated day the strategy sees ONLY candles up to that day (the prefix),
exactly as it would have live — no lookahead is possible by construction
(ADR-007). Execution model, kept deliberately honest and simple:

- A bullish verdict (confidence >= config.entry_confidence) fills at the NEXT
  bar's open (you can't trade a close you've only just observed).
- The stop captured at entry exits intraday when the bar's low touches it
  (gap-downs fill at the open, not at the wished-for stop).
- A verdict flipping to non-bullish exits at the next bar's open.
- Costs are charged per side. One position at a time, full equity per trade
  (position sizing arrives in a later milestone).
"""

import math
from statistics import pstdev

from arcturus_api.domain.backtest.models import BacktestConfig, BacktestResult, BacktestTrade
from arcturus_api.domain.market.models import CandleSeries
from arcturus_api.domain.strategy.base import Strategy
from arcturus_api.domain.strategy.models import InsufficientHistoryError, Stance

_TRADING_DAYS_PER_YEAR = 252


def run_backtest(
    strategy: Strategy, candles: CandleSeries, config: BacktestConfig | None = None
) -> BacktestResult:
    config = config or BacktestConfig()
    series = candles.candles
    if len(series) <= strategy.min_candles + 1:
        raise InsufficientHistoryError(strategy.metadata.key, strategy.min_candles + 2, len(series))

    cost = config.cost_per_side_pct / 100.0
    closes = [float(candle.close) for candle in series]

    equity = 1.0
    equity_curve: list[float] = []
    trades: list[BacktestTrade] = []

    in_position = False
    entry_price = 0.0
    entry_index = 0
    stop: float | None = None
    pending_entry = False
    pending_exit_reason: str | None = None
    bars_in_position = 0

    for index in range(strategy.min_candles, len(series)):
        bar = series[index]
        open_, low, close = float(bar.open), float(bar.low), float(bar.close)

        # 1) Execute orders queued from yesterday's verdict at today's open
        if not in_position and pending_entry:
            in_position = True
            entry_price = open_ * (1 + cost)
            entry_index = index
            pending_entry = False
        elif in_position and pending_exit_reason is not None:
            _close_trade(
                trades,
                series,
                entry_index,
                index,
                entry_price,
                open_ * (1 - cost),
                pending_exit_reason,
            )
            equity *= 1 + trades[-1].return_pct / 100
            in_position = False
            pending_exit_reason = None
            stop = None

        # 2) Intraday stop check
        if in_position and stop is not None and low <= stop:
            fill = min(open_, stop)  # gap through the stop fills at the open
            _close_trade(trades, series, entry_index, index, entry_price, fill * (1 - cost), "stop")
            equity *= 1 + trades[-1].return_pct / 100
            in_position = False
            stop = None
            pending_exit_reason = None

        # 3) Evaluate the strategy on the prefix ending at today's close
        prefix = CandleSeries(
            symbol=candles.symbol, interval=candles.interval, candles=series[: index + 1]
        )
        verdict = strategy.evaluate(prefix)

        if not in_position and not pending_entry:
            if verdict.stance == Stance.BULLISH and verdict.confidence >= config.entry_confidence:
                pending_entry = True
                stop = float(verdict.stop_loss) if verdict.stop_loss is not None else None
        elif in_position and pending_exit_reason is None and verdict.stance != Stance.BULLISH:
            pending_exit_reason = "signal_flip"

        # 4) Mark equity to market
        if in_position:
            bars_in_position += 1
            equity_curve.append(equity * (close * (1 - cost)) / entry_price)
        else:
            equity_curve.append(equity)

    # Close any open position at the final close
    if in_position:
        final = series[-1]
        _close_trade(
            trades,
            series,
            entry_index,
            len(series) - 1,
            entry_price,
            float(final.close) * (1 - cost),
            "end_of_data",
        )
        equity *= 1 + trades[-1].return_pct / 100
        equity_curve[-1] = equity

    first_close = closes[strategy.min_candles]
    buy_hold = (closes[-1] / first_close - 1) * 100

    wins = [trade.return_pct for trade in trades if trade.return_pct > 0]
    losses = [trade.return_pct for trade in trades if trade.return_pct <= 0]

    return BacktestResult(
        strategy=strategy.metadata,
        symbol=candles.symbol,
        start=series[strategy.min_candles].timestamp,
        end=series[-1].timestamp,
        bars=len(equity_curve),
        config=config,
        trades=trades,
        total_return_pct=round((equity - 1) * 100, 2),
        buy_hold_return_pct=round(buy_hold, 2),
        win_rate_pct=round(len(wins) / len(trades) * 100, 1) if trades else None,
        average_win_pct=round(sum(wins) / len(wins), 2) if wins else None,
        average_loss_pct=round(sum(losses) / len(losses), 2) if losses else None,
        max_drawdown_pct=round(_max_drawdown(equity_curve), 2),
        exposure_pct=round(bars_in_position / len(equity_curve) * 100, 1),
        annualized_sharpe=_sharpe(equity_curve),
    )


def _close_trade(
    trades: list[BacktestTrade],
    series: list,  # type: ignore[type-arg]
    entry_index: int,
    exit_index: int,
    entry_price: float,
    exit_price: float,
    reason: str,
) -> None:
    trades.append(
        BacktestTrade(
            entry_date=series[entry_index].timestamp,
            entry_price=round(entry_price, 4),
            exit_date=series[exit_index].timestamp,
            exit_price=round(exit_price, 4),
            exit_reason=reason,
            return_pct=round((exit_price / entry_price - 1) * 100, 4),
        )
    )


def _max_drawdown(equity_curve: list[float]) -> float:
    peak = -math.inf
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        worst = min(worst, (value / peak - 1) * 100)
    return worst


def _sharpe(equity_curve: list[float]) -> float | None:
    if len(equity_curve) < 30:
        return None
    daily_returns = [
        equity_curve[index] / equity_curve[index - 1] - 1 for index in range(1, len(equity_curve))
    ]
    deviation = pstdev(daily_returns)
    if deviation == 0:
        return None
    mean = sum(daily_returns) / len(daily_returns)
    return round(mean / deviation * math.sqrt(_TRADING_DAYS_PER_YEAR), 2)
