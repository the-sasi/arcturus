"""Tier 1 strategy plugins: EMA crossover, RSI mean-reversion, range breakout.

Every rule is deterministic and every verdict carries number-backed reasons.
Confidence is a rule-scored heuristic (0-100), NOT a probability of profit.
"""

from decimal import Decimal

from arcturus_api.domain.indicators.library import atr, ema, rsi, sma
from arcturus_api.domain.market.models import CandleSeries
from arcturus_api.domain.strategy.base import Strategy
from arcturus_api.domain.strategy.models import (
    InsufficientHistoryError,
    PriceZone,
    Stance,
    StrategyMetadata,
    StrategyVerdict,
)


def _decimal(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def _series_data(candles: CandleSeries) -> tuple[list[float], list[float], list[float], list[int]]:
    closes = [float(candle.close) for candle in candles.candles]
    highs = [float(candle.high) for candle in candles.candles]
    lows = [float(candle.low) for candle in candles.candles]
    volumes = [candle.volume for candle in candles.candles]
    return closes, highs, lows, volumes


def _require(strategy: Strategy, candles: CandleSeries) -> None:
    if len(candles.candles) < strategy.min_candles:
        raise InsufficientHistoryError(
            strategy.metadata.key, strategy.min_candles, len(candles.candles)
        )


class EmaCrossoverStrategy(Strategy):
    metadata = StrategyMetadata(
        key="ema_crossover",
        name="EMA 20/50 Crossover",
        version="1.0.0",
        style="trend-following",
        description=(
            "Follows the medium-term trend: bullish when the 20-day EMA is above "
            "the 50-day EMA, with freshness, price and volume confirmation."
        ),
        typical_holding="2-8 weeks",
    )
    min_candles = 60

    def evaluate(self, candles: CandleSeries) -> StrategyVerdict:
        _require(self, candles)
        closes, highs, lows, volumes = _series_data(candles)
        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        atr14 = atr(highs, lows, closes, 14)

        e20, e50 = ema20[-1], ema50[-1]
        assert e20 is not None and e50 is not None
        close = closes[-1]
        spread_pct = (e20 - e50) / e50 * 100

        # How many bars since the EMAs last crossed
        bars_since_cross = 0
        current_sign = e20 >= e50
        for index in range(len(closes) - 1, 0, -1):
            a, b = ema20[index], ema50[index]
            if a is None or b is None:
                break
            if (a >= b) != current_sign:
                break
            bars_since_cross += 1

        recent_volume = sum(volumes[-5:]) / 5
        base_volume = sum(volumes[-20:]) / 20
        volume_ratio = recent_volume / base_volume if base_volume else 1.0

        reasons: list[str] = []
        if abs(spread_pct) < 0.25:
            stance = Stance.NEUTRAL
            confidence = 35
            reasons.append(
                f"EMA20 ({e20:.2f}) and EMA50 ({e50:.2f}) are within 0.25% — no clear trend."
            )
        else:
            bullish = e20 > e50
            stance = Stance.BULLISH if bullish else Stance.BEARISH
            direction = "above" if bullish else "below"
            confidence = 50
            reasons.append(
                f"EMA20 ({e20:.2f}) is {direction} EMA50 ({e50:.2f}) by {abs(spread_pct):.2f}%."
            )
            if bars_since_cross <= 10:
                confidence += 15
                reasons.append(f"Fresh crossover: only {bars_since_cross} sessions ago.")
            else:
                reasons.append(f"Crossover happened {bars_since_cross} sessions ago.")
            price_confirms = close > e20 if bullish else close < e20
            if price_confirms:
                confidence += 10
                reasons.append(f"Price ({close:.2f}) confirms, trading {direction} EMA20.")
            if volume_ratio > 1.2:
                confidence += 10
                reasons.append(
                    f"Volume expanding: last 5 days {volume_ratio:.1f}x the 20-day average."
                )
            if abs(spread_pct) > 6:
                confidence -= 10
                reasons.append(
                    f"Stretched: EMAs {abs(spread_pct):.1f}% apart — "
                    "late-stage trend, pullback risk."
                )

        entry_zone = None
        stop_loss = None
        last_atr = atr14[-1]
        if stance == Stance.BULLISH and last_atr is not None:
            entry_zone = PriceZone(low=_decimal(min(e20, close)), high=_decimal(close))
            stop_loss = _decimal(close - 2 * last_atr)
            reasons.append(f"Suggested stop {stop_loss} = close - 2xATR(14) ({last_atr:.2f}).")

        return StrategyVerdict(
            strategy=self.metadata,
            symbol=candles.symbol,
            stance=stance,
            confidence=max(0, min(confidence, 90)),
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            reasons=reasons,
            as_of=candles.candles[-1].timestamp,
        )


class RsiMeanReversionStrategy(Strategy):
    metadata = StrategyMetadata(
        key="rsi_mean_reversion",
        name="RSI Mean-Reversion",
        version="1.0.0",
        style="mean-reversion",
        description=(
            "Buys oversold dips (RSI < 35) in stocks trading above their 100-day "
            "average; flags overbought rallies in downtrends as bearish."
        ),
        typical_holding="3-10 days",
    )
    min_candles = 120

    def evaluate(self, candles: CandleSeries) -> StrategyVerdict:
        _require(self, candles)
        closes, highs, lows, _ = _series_data(candles)
        rsi14 = rsi(closes, 14)
        sma100 = sma(closes, 100)
        atr14 = atr(highs, lows, closes, 14)

        current_rsi, previous_rsi = rsi14[-1], rsi14[-2]
        trend_line = sma100[-1]
        assert current_rsi is not None and previous_rsi is not None and trend_line is not None
        close = closes[-1]
        in_uptrend = close > trend_line

        reasons: list[str] = [
            f"RSI(14) is {current_rsi:.1f}; price {close:.2f} is "
            f"{'above' if in_uptrend else 'below'} the 100-day average ({trend_line:.2f})."
        ]
        stance = Stance.NEUTRAL
        confidence = 30

        if current_rsi < 35 and in_uptrend:
            stance = Stance.BULLISH
            confidence = 50 + min(int((35 - current_rsi) * 2), 25)
            reasons.append("Oversold dip inside an uptrend — classic swing bounce setup.")
            if current_rsi > previous_rsi:
                confidence += 10
                reasons.append(
                    f"RSI turning up ({previous_rsi:.1f} → {current_rsi:.1f}) — "
                    "selling pressure easing."
                )
            else:
                reasons.append(
                    "RSI still falling — knife not done dropping; smaller size warranted."
                )
        elif current_rsi > 70 and not in_uptrend:
            stance = Stance.BEARISH
            confidence = 55 + min(int((current_rsi - 70) * 2), 20)
            reasons.append("Overbought rally inside a downtrend — bounce likely to fade.")
        elif current_rsi < 35 and not in_uptrend:
            reasons.append(
                "Oversold but in a downtrend — no edge: falling stocks can stay oversold."
            )
        else:
            reasons.append("No RSI extreme — mean-reversion has no setup here.")

        entry_zone = None
        stop_loss = None
        last_atr = atr14[-1]
        if stance == Stance.BULLISH and last_atr is not None:
            ten_day_low = min(lows[-10:])
            entry_zone = PriceZone(low=_decimal(close * 0.995), high=_decimal(close * 1.005))
            stop_loss = _decimal(min(ten_day_low, close - 2 * last_atr))
            reasons.append(
                f"Suggested stop {stop_loss} = below 10-day low ({ten_day_low:.2f}) and 2xATR."
            )

        return StrategyVerdict(
            strategy=self.metadata,
            symbol=candles.symbol,
            stance=stance,
            confidence=max(0, min(confidence, 90)),
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            reasons=reasons,
            as_of=candles.candles[-1].timestamp,
        )


class RangeBreakoutStrategy(Strategy):
    metadata = StrategyMetadata(
        key="range_breakout",
        name="20-Day Range Breakout",
        version="1.0.0",
        style="breakout",
        description=(
            "Signals when price clears its prior 20-day high on expanding volume; "
            "breakdowns below the 20-day low are bearish."
        ),
        typical_holding="2-6 weeks",
    )
    min_candles = 40

    def evaluate(self, candles: CandleSeries) -> StrategyVerdict:
        _require(self, candles)
        closes, highs, lows, volumes = _series_data(candles)
        close = closes[-1]
        prior_high = max(highs[-21:-1])
        prior_low = min(lows[-21:-1])
        volume_today = volumes[-1]
        average_volume = sum(volumes[-21:-1]) / 20
        volume_ratio = volume_today / average_volume if average_volume else 1.0
        day_high, day_low = highs[-1], lows[-1]
        close_strength = (close - day_low) / (day_high - day_low) if day_high > day_low else 0.5

        reasons: list[str] = []
        stance = Stance.NEUTRAL
        confidence = 30

        if close > prior_high:
            reasons.append(f"Close {close:.2f} cleared the prior 20-day high ({prior_high:.2f}).")
            if volume_ratio >= 1.5:
                stance = Stance.BULLISH
                confidence = 55
                reasons.append(f"Volume confirms: {volume_ratio:.1f}x the 20-day average.")
                if volume_ratio >= 2.0:
                    confidence += 10
                if close_strength >= 0.7:
                    confidence += 10
                    reasons.append("Strong close — finished in the top 30% of the day's range.")
            else:
                reasons.append(
                    f"But volume is only {volume_ratio:.1f}x average — "
                    "unconfirmed breakout, prone to failure."
                )
                confidence = 40
        elif close < prior_low:
            stance = Stance.BEARISH
            confidence = 55 if volume_ratio >= 1.5 else 45
            reasons.append(
                f"Close {close:.2f} broke below the prior 20-day low ({prior_low:.2f})"
                f"{' on heavy volume' if volume_ratio >= 1.5 else ''}."
            )
        else:
            distance = (prior_high - close) / close * 100
            reasons.append(
                f"Inside the range: {distance:.1f}% below the 20-day high "
                f"({prior_high:.2f}) — no breakout."
            )
            if distance <= 2:
                confidence = 40
                reasons.append("Coiling just under resistance — worth watching for a volume push.")

        entry_zone = None
        stop_loss = None
        if stance == Stance.BULLISH:
            entry_zone = PriceZone(low=_decimal(prior_high), high=_decimal(close))
            stop_loss = _decimal(prior_high * 0.97)
            reasons.append(
                f"Suggested stop {stop_loss} = 3% under the breakout level (failed-breakout exit)."
            )

        return StrategyVerdict(
            strategy=self.metadata,
            symbol=candles.symbol,
            stance=stance,
            confidence=max(0, min(confidence, 90)),
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            reasons=reasons,
            as_of=candles.candles[-1].timestamp,
        )


ALL_STRATEGIES: tuple[Strategy, ...] = (
    EmaCrossoverStrategy(),
    RsiMeanReversionStrategy(),
    RangeBreakoutStrategy(),
)
