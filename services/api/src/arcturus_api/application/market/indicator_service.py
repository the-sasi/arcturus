"""Indicator computation use cases.

Computes deterministic indicators over (cached) candle history. Parsing and
math live in the domain; this service only orchestrates.
"""

import re

from arcturus_api.application.market.service import MarketDataService
from arcturus_api.domain.indicators.library import Series, bollinger, ema, macd, rsi, sma
from arcturus_api.domain.indicators.models import IndicatorSeries, UnknownIndicatorError
from arcturus_api.domain.market.models import Interval

_SPEC_PATTERN = re.compile(r"^(sma|ema|rsi|bollinger):(\d{1,3})$|^(macd)$")
_MAX_PERIOD = 500


class IndicatorService:
    def __init__(self, market: MarketDataService) -> None:
        self._market = market

    async def compute(
        self,
        raw_symbol: str,
        interval: Interval,
        specs: list[str],
    ) -> IndicatorSeries:
        candles = await self._market.get_candles(raw_symbol, interval)
        closes = [float(candle.close) for candle in candles.candles]

        series: dict[str, list[float | None]] = {}
        for raw_spec in specs:
            spec = raw_spec.strip().lower()
            for name, values in self._compute_one(spec, closes).items():
                series[name] = [round(value, 4) if value is not None else None for value in values]

        return IndicatorSeries(
            symbol=candles.symbol,
            interval=interval,
            timestamps=[candle.timestamp.isoformat() for candle in candles.candles],
            series=series,
        )

    def _compute_one(self, spec: str, closes: list[float]) -> dict[str, Series]:
        match = _SPEC_PATTERN.match(spec)
        if match is None:
            raise UnknownIndicatorError(spec)
        if match.group(3) == "macd":
            line, signal, histogram = macd(closes)
            return {"macd": line, "macd_signal": signal, "macd_histogram": histogram}
        name, period_text = match.group(1), match.group(2)
        period = int(period_text)
        if not 1 <= period <= _MAX_PERIOD:
            raise UnknownIndicatorError(spec)
        if name == "sma":
            return {f"sma_{period}": sma(closes, period)}
        if name == "ema":
            return {f"ema_{period}": ema(closes, period)}
        if name == "rsi":
            return {f"rsi_{period}": rsi(closes, period)}
        upper, middle, lower = bollinger(closes, period)
        return {
            f"bb_upper_{period}": upper,
            f"bb_middle_{period}": middle,
            f"bb_lower_{period}": lower,
        }
