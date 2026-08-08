"""Indicator series domain models."""

from pydantic import BaseModel, ConfigDict

from arcturus_api.domain.market.models import Interval, Symbol


class IndicatorSeries(BaseModel):
    """Indicator values aligned 1:1 with the candle timestamps."""

    model_config = ConfigDict(frozen=True)

    symbol: Symbol
    interval: Interval
    timestamps: list[str]
    series: dict[str, list[float | None]]


class UnknownIndicatorError(Exception):
    def __init__(self, spec: str) -> None:
        self.spec = spec
        super().__init__(
            f"Unknown indicator spec '{spec}'. Supported: sma:N, ema:N, rsi:N, macd, bollinger:N"
        )
