import math

import pytest

from arcturus_api.domain.indicators.library import bollinger, ema, macd, rsi, sma


def approx(value: float | None, expected: float) -> bool:
    assert value is not None
    return math.isclose(value, expected, rel_tol=1e-9)


class TestSma:
    def test_golden(self) -> None:
        assert sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]

    def test_shorter_than_period(self) -> None:
        assert sma([1.0, 2.0], 5) == [None, None]


class TestEma:
    def test_golden_seeded_with_sma(self) -> None:
        result = ema([1, 2, 3, 4, 5], 3)
        assert result[:2] == [None, None]
        assert approx(result[2], 2.0)
        assert approx(result[3], 3.0)  # (4-2)*0.5 + 2
        assert approx(result[4], 4.0)  # (5-3)*0.5 + 3


class TestRsi:
    def test_all_gains_is_100(self) -> None:
        result = rsi([1, 2, 3, 4, 5, 6], 3)
        assert result[3] == 100.0

    def test_wilder_smoothing_golden(self) -> None:
        result = rsi([1, 2, 3, 4, 3, 2], 3)
        assert result[3] == 100.0
        assert approx(result[4], 100.0 - 100.0 / (1.0 + (2.0 / 3.0) / (1.0 / 3.0)))
        avg_gain_5 = (2.0 / 3.0 * 2) / 3
        avg_loss_5 = (1.0 / 3.0 * 2 + 1) / 3
        assert approx(result[5], 100.0 - 100.0 / (1.0 + avg_gain_5 / avg_loss_5))

    def test_undefined_until_period(self) -> None:
        assert rsi([1, 2, 3], 14) == [None, None, None]


class TestMacd:
    def test_uptrend_line_positive_and_alignment(self) -> None:
        closes = [float(value) for value in range(1, 60)]
        line, signal, histogram = macd(closes)
        assert len(line) == len(signal) == len(histogram) == len(closes)
        assert line[24] is None  # slow EMA(26) undefined until index 25
        assert line[25] is not None and line[25] > 0
        assert signal[32] is None  # signal EMA(9) needs 9 defined MACD values
        assert signal[33] is not None
        assert histogram[33] is not None

    def test_invalid_periods_raise(self) -> None:
        with pytest.raises(ValueError):
            macd([1.0, 2.0], fast=26, slow=12)


class TestBollinger:
    def test_constant_series_bands_collapse(self) -> None:
        upper, middle, lower = bollinger([5.0] * 25, period=20)
        assert approx(upper[24], 5.0)
        assert approx(middle[24], 5.0)
        assert approx(lower[24], 5.0)

    def test_bands_bracket_sma(self) -> None:
        closes = [float(1 + (index % 5)) for index in range(30)]
        upper, middle, lower = bollinger(closes, period=20)
        assert upper[29] is not None and middle[29] is not None and lower[29] is not None
        assert upper[29] > middle[29] > lower[29]
