"""Data Quality Engine: candle validation rules (R2)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from arcturus_api.domain.market.models import Candle, CandleSeries, Interval, Symbol
from arcturus_api.domain.quality.candles import assess_candles
from arcturus_api.domain.quality.models import DataQualityReport, QualityDimension, QualityStatus

NOW = datetime(2026, 9, 15, 12, tzinfo=UTC)
YESTERDAY = NOW - timedelta(days=1)


def bar(
    when: datetime,
    open_: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
    volume: int = 1000,
) -> Candle:
    return Candle(
        timestamp=when,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=volume,
    )


def daily(count: int, last: datetime = YESTERDAY) -> list[Candle]:
    return [bar(last - timedelta(days=count - 1 - index)) for index in range(count)]


def series(
    candles: list[Candle], symbol: str = "NSE:TEST", interval: Interval = Interval.DAY_1
) -> CandleSeries:
    return CandleSeries(symbol=Symbol.parse(symbol), interval=interval, candles=candles)


def checks(report: DataQualityReport) -> set[str]:
    return {issue.check for issue in report.issues}


class TestValidSeries:
    def test_clean_series_is_valid(self) -> None:
        report = assess_candles(series(daily(30)), NOW, source_id="yahoo")
        assert report.status == QualityStatus.VALID
        assert report.issues == []
        assert report.records_checked == 30
        assert report.source_id == "yahoo"
        assert set(report.dimensions) == {
            QualityDimension.COMPLETENESS,
            QualityDimension.VALIDITY,
            QualityDimension.CONSISTENCY,
            QualityDimension.DUPLICATION,
            QualityDimension.FRESHNESS,
        }

    def test_vendor_rounding_within_tolerance_is_valid(self) -> None:
        candles = daily(10)
        candles[3] = bar(candles[3].timestamp, high="100", close="100.005")
        assert assess_candles(series(candles), NOW).status == QualityStatus.VALID

    def test_weekend_gap_is_not_flagged(self) -> None:
        candles = daily(20)
        del candles[5:7]  # 3-day gap
        assert assess_candles(series(candles), NOW).status == QualityStatus.VALID


class TestInvalidSeries:
    def test_empty_series(self) -> None:
        report = assess_candles(series([]), NOW)
        assert report.status == QualityStatus.INVALID
        assert checks(report) == {"empty_series"}

    def test_high_below_low(self) -> None:
        candles = daily(10)
        candles[4] = bar(candles[4].timestamp, high="98", low="99")
        report = assess_candles(series(candles), NOW)
        assert report.status == QualityStatus.INVALID
        assert report.dimensions[QualityDimension.VALIDITY] == QualityStatus.INVALID
        issue = next(issue for issue in report.issues if issue.check == "high_below_low")
        assert issue.examples == [candles[4].timestamp.isoformat()]

    def test_close_outside_range(self) -> None:
        candles = daily(10)
        candles[2] = bar(candles[2].timestamp, close="105")
        assert "open_close_outside_range" in checks(assess_candles(series(candles), NOW))

    def test_non_positive_price(self) -> None:
        candles = daily(10)
        candles[2] = bar(candles[2].timestamp, low="0")
        assert "non_positive_price" in checks(assess_candles(series(candles), NOW))

    def test_negative_volume(self) -> None:
        candles = daily(10)
        candles[2] = bar(candles[2].timestamp, volume=-5)
        assert "negative_volume" in checks(assess_candles(series(candles), NOW))

    def test_duplicate_session(self) -> None:
        candles = daily(10)
        candles.append(bar(candles[-1].timestamp + timedelta(hours=5)))  # same trading date
        report = assess_candles(series(candles), NOW)
        assert report.status == QualityStatus.INVALID
        assert report.dimensions[QualityDimension.DUPLICATION] == QualityStatus.INVALID

    def test_out_of_order(self) -> None:
        candles = daily(10)
        candles[3], candles[4] = candles[4], candles[3]
        report = assess_candles(series(candles), NOW)
        assert report.dimensions[QualityDimension.CONSISTENCY] == QualityStatus.INVALID

    def test_worst_status_wins(self) -> None:
        candles = daily(40)
        del candles[10:20]  # warning: gap
        candles[25] = bar(candles[25].timestamp, high="98", low="99")  # invalid
        report = assess_candles(series(candles), NOW)
        assert report.status == QualityStatus.INVALID
        assert report.dimensions[QualityDimension.COMPLETENESS] == QualityStatus.WARNING


class TestWarnings:
    def test_long_gap(self) -> None:
        candles = daily(40)
        del candles[10:20]
        report = assess_candles(series(candles), NOW)
        assert report.status == QualityStatus.WARNING
        assert "calendar_gap" in checks(report)

    def test_stale_series(self) -> None:
        report = assess_candles(series(daily(30, last=NOW - timedelta(days=10))), NOW)
        assert report.status == QualityStatus.WARNING
        assert report.dimensions[QualityDimension.FRESHNESS] == QualityStatus.WARNING

    def test_zero_volume_flagged_for_equities_not_indices(self) -> None:
        candles = [bar(candle.timestamp, volume=0) for candle in daily(10)]
        assert "zero_volume" in checks(assess_candles(series(candles), NOW))
        index_report = assess_candles(series(candles, symbol="INDEX:^NSEI"), NOW)
        assert index_report.status == QualityStatus.VALID

    def test_extreme_move(self) -> None:
        candles = daily(20)
        candles[15] = bar(candles[15].timestamp, open_="200", high="201", low="199", close="200")
        report = assess_candles(series(candles), NOW)
        assert report.status == QualityStatus.WARNING
        assert "extreme_move" in checks(report)

    def test_intraday_skips_calendar_rules(self) -> None:
        old = NOW - timedelta(days=30)
        candles = [bar(old + timedelta(hours=hour * 20)) for hour in range(10)]
        report = assess_candles(series(candles, interval=Interval.HOUR_1), NOW)
        assert report.status == QualityStatus.VALID
        assert QualityDimension.FRESHNESS not in report.dimensions
