"""Backtest domain models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from arcturus_api.domain.market.models import Symbol
from arcturus_api.domain.strategy.models import StrategyMetadata


class BacktestConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Percent cost per side (brokerage + taxes + slippage). 0.2%/side default
    # is a realistic Indian delivery-trade estimate.
    cost_per_side_pct: float = 0.2
    # Only act on bullish verdicts at or above this confidence
    entry_confidence: int = 55


class BacktestTrade(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    exit_reason: str  # "stop" | "signal_flip" | "end_of_data"
    return_pct: float  # net of costs


class BacktestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: StrategyMetadata
    symbol: Symbol
    start: datetime
    end: datetime
    bars: int
    config: BacktestConfig

    trades: list[BacktestTrade]
    total_return_pct: float  # strategy equity, net of costs
    buy_hold_return_pct: float  # same window, buy first close hold to last
    win_rate_pct: float | None  # None when no trades
    average_win_pct: float | None
    average_loss_pct: float | None
    max_drawdown_pct: float  # worst peak-to-trough of strategy equity
    exposure_pct: float  # share of bars spent in a position
    annualized_sharpe: float | None  # from daily equity returns; None if degenerate
