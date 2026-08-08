"""Deterministic technical indicator library.

Pure functions over close-price sequences. This is the calculation layer the
blueprint mandates stays OUT of LLM prompts — agents may cite these values,
never compute them.

All functions return a list aligned 1:1 with the input; positions where the
indicator is not yet defined hold None.
"""

import math

Series = list[float | None]


def sma(closes: list[float], period: int) -> Series:
    """Simple moving average."""
    _validate(closes, period)
    out: Series = [None] * len(closes)
    window_sum = 0.0
    for index, close in enumerate(closes):
        window_sum += close
        if index >= period:
            window_sum -= closes[index - period]
        if index >= period - 1:
            out[index] = window_sum / period
    return out


def ema(closes: list[float], period: int) -> Series:
    """Exponential moving average, seeded with the SMA of the first window."""
    _validate(closes, period)
    out: Series = [None] * len(closes)
    if len(closes) < period:
        return out
    seed = sum(closes[:period]) / period
    out[period - 1] = seed
    multiplier = 2 / (period + 1)
    previous = seed
    for index in range(period, len(closes)):
        previous = (closes[index] - previous) * multiplier + previous
        out[index] = previous
    return out


def rsi(closes: list[float], period: int = 14) -> Series:
    """Relative Strength Index with Wilder's smoothing."""
    _validate(closes, period)
    out: Series = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = 0.0
    losses = 0.0
    for index in range(1, period + 1):
        change = closes[index] - closes[index - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[index] = _rsi_value(avg_gain, avg_loss)
    return out


def macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[Series, Series, Series]:
    """MACD line, signal line, histogram."""
    if not fast < slow:
        raise ValueError("MACD fast period must be < slow period")
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    line: Series = [
        f - s if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema, strict=True)
    ]
    defined = [value for value in line if value is not None]
    signal_on_defined = ema(defined, signal) if len(defined) >= signal else [None] * len(defined)
    signal_line: Series = [None] * len(line)
    cursor = 0
    for index, value in enumerate(line):
        if value is not None:
            signal_line[index] = signal_on_defined[cursor]
            cursor += 1
    histogram: Series = [
        m - s if m is not None and s is not None else None
        for m, s in zip(line, signal_line, strict=True)
    ]
    return line, signal_line, histogram


def bollinger(
    closes: list[float], period: int = 20, num_std: float = 2.0
) -> tuple[Series, Series, Series]:
    """Bollinger bands: (upper, middle/SMA, lower)."""
    middle = sma(closes, period)
    upper: Series = [None] * len(closes)
    lower: Series = [None] * len(closes)
    for index in range(period - 1, len(closes)):
        window = closes[index - period + 1 : index + 1]
        mean = middle[index]
        assert mean is not None
        variance = sum((value - mean) ** 2 for value in window) / period
        deviation = math.sqrt(variance) * num_std
        upper[index] = mean + deviation
        lower[index] = mean - deviation
    return upper, middle, lower


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> Series:
    """Average True Range with Wilder's smoothing."""
    if not len(highs) == len(lows) == len(closes):
        raise ValueError("highs/lows/closes must be the same length")
    _validate(closes, period)
    length = len(closes)
    out: Series = [None] * length
    if length <= period:
        return out
    true_ranges = [highs[0] - lows[0]]
    for index in range(1, length):
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )
    previous = sum(true_ranges[1 : period + 1]) / period
    out[period] = previous
    for index in range(period + 1, length):
        previous = (previous * (period - 1) + true_ranges[index]) / period
        out[index] = previous
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        # No losses: fully overbought — unless there are no gains either
        # (flat series), which is neutral, not overbought.
        return 50.0 if avg_gain == 0 else 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def _validate(closes: list[float], period: int) -> None:
    if period < 1:
        raise ValueError("period must be >= 1")
