"""Deterministic OHLCV candle validation (R2).

One bad bar — high below low, a duplicated session, a stale feed — silently
manufactures fake edges in a backtest, so candles are checked before use.

INVALID (cannot be trusted for computation):
  empty series · non-positive prices · high below low · open/close outside the
  bar's range · negative volume · out-of-order timestamps · duplicate sessions
WARNING (usable, but must be visible):
  calendar gaps · stale last bar · zero-volume bars (not for indices) ·
  close-to-close moves over 50% (possible unadjusted split/bonus or bad tick)

Gap and staleness rules apply to daily-or-longer intervals only; intraday
series have overnight/holiday gaps that a calendar rule cannot judge.
"""

from datetime import datetime
from decimal import Decimal

from arcturus_api.domain.market.models import Candle, CandleSeries, Exchange, Interval
from arcturus_api.domain.quality.models import (
    DataQualityReport,
    QualityDimension,
    QualityIssue,
    QualityStatus,
    build_report,
)

CANDLE_RULES_VERSION = "1.0.0"

# Relative tolerance absorbing vendor rounding (Yahoo prices are rounded to 4dp)
_PRICE_TOLERANCE = Decimal("0.0001")
_EXTREME_MOVE = Decimal("0.5")
_MAX_EXAMPLES = 5

# Calendar days allowed between consecutive bars, and maximum age of the last
# bar. Daily limits cover weekends plus multi-day Indian exchange holidays.
_GAP_DAYS: dict[Interval, int] = {Interval.DAY_1: 7, Interval.WEEK_1: 21, Interval.MONTH_1: 62}
_STALE_DAYS: dict[Interval, int] = {Interval.DAY_1: 5, Interval.WEEK_1: 14, Interval.MONTH_1: 45}


def assess_candles(
    series: CandleSeries, now: datetime, source_id: str | None = None
) -> DataQualityReport:
    candles = series.candles
    daily_or_longer = series.interval in _GAP_DAYS
    checked = [
        QualityDimension.COMPLETENESS,
        QualityDimension.VALIDITY,
        QualityDimension.CONSISTENCY,
        QualityDimension.DUPLICATION,
    ]
    if daily_or_longer:
        checked.append(QualityDimension.FRESHNESS)

    issues: list[QualityIssue] = []
    if not candles:
        issues.append(
            QualityIssue(
                check="empty_series",
                dimension=QualityDimension.COMPLETENESS,
                severity=QualityStatus.INVALID,
                message="no candles returned",
                count=1,
            )
        )
    else:
        check_zero_volume = series.symbol.exchange != Exchange.INDEX
        issues += _validity_issues(candles, check_zero_volume)
        issues += _ordering_issues(candles, by_date=daily_or_longer)
        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        issues += _extreme_move_issues(ordered)
        if daily_or_longer:
            issues += _gap_issues(ordered, _GAP_DAYS[series.interval])
            issues += _staleness_issues(ordered[-1], now, _STALE_DAYS[series.interval])

    return build_report(
        dataset="ohlcv_candles",
        subject=f"{series.symbol} {series.interval.value}",
        source_id=source_id,
        checked=checked,
        issues=issues,
        records_checked=len(candles),
        rules_version=CANDLE_RULES_VERSION,
        checked_at=now,
    )


def _issue(
    check: str,
    dimension: QualityDimension,
    severity: QualityStatus,
    what: str,
    hits: list[str],
) -> list[QualityIssue]:
    if not hits:
        return []
    return [
        QualityIssue(
            check=check,
            dimension=dimension,
            severity=severity,
            message=f"{len(hits)} {what}",
            count=len(hits),
            examples=hits[:_MAX_EXAMPLES],
        )
    ]


def _label(candle: Candle) -> str:
    return candle.timestamp.isoformat()


def _validity_issues(candles: list[Candle], check_zero_volume: bool) -> list[QualityIssue]:
    non_positive: list[str] = []
    high_below_low: list[str] = []
    outside_range: list[str] = []
    negative_volume: list[str] = []
    zero_volume: list[str] = []

    for candle in candles:
        if candle.volume < 0:
            negative_volume.append(_label(candle))
        elif candle.volume == 0 and check_zero_volume:
            zero_volume.append(_label(candle))

        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            non_positive.append(_label(candle))
            continue
        tolerance = candle.high * _PRICE_TOLERANCE
        if candle.low - candle.high > tolerance:
            high_below_low.append(_label(candle))
            continue
        lowest, highest = candle.low - tolerance, candle.high + tolerance
        if not (lowest <= candle.open <= highest and lowest <= candle.close <= highest):
            outside_range.append(_label(candle))

    invalid = QualityStatus.INVALID
    validity = QualityDimension.VALIDITY
    return [
        *_issue(
            "non_positive_price", validity, invalid, "bar(s) with non-positive prices", non_positive
        ),
        *_issue("high_below_low", validity, invalid, "bar(s) with high below low", high_below_low),
        *_issue(
            "open_close_outside_range",
            validity,
            invalid,
            "bar(s) with open/close outside the high-low range",
            outside_range,
        ),
        *_issue(
            "negative_volume", validity, invalid, "bar(s) with negative volume", negative_volume
        ),
        *_issue(
            "zero_volume", validity, QualityStatus.WARNING, "bar(s) with zero volume", zero_volume
        ),
    ]


def _ordering_issues(candles: list[Candle], by_date: bool) -> list[QualityIssue]:
    out_of_order: list[str] = []
    duplicates: list[str] = []
    seen: set[object] = set()
    previous: datetime | None = None

    for candle in candles:
        key: object = candle.timestamp.date() if by_date else candle.timestamp
        if key in seen:
            duplicates.append(_label(candle))
        seen.add(key)
        if previous is not None and candle.timestamp < previous:
            out_of_order.append(_label(candle))
        previous = candle.timestamp

    return [
        *_issue(
            "out_of_order",
            QualityDimension.CONSISTENCY,
            QualityStatus.INVALID,
            "bar(s) out of chronological order",
            out_of_order,
        ),
        *_issue(
            "duplicate_session",
            QualityDimension.DUPLICATION,
            QualityStatus.INVALID,
            "duplicate session(s)",
            duplicates,
        ),
    ]


def _extreme_move_issues(ordered: list[Candle]) -> list[QualityIssue]:
    hits: list[str] = []
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if previous.close <= 0:
            continue
        move = abs(current.close / previous.close - 1)
        if move > _EXTREME_MOVE:
            hits.append(f"{_label(current)} ({move * 100:.0f}%)")
    return _issue(
        "extreme_move",
        QualityDimension.VALIDITY,
        QualityStatus.WARNING,
        "close-to-close move(s) over 50% (possible unadjusted split/bonus or bad tick)",
        hits,
    )


def _gap_issues(ordered: list[Candle], max_days: int) -> list[QualityIssue]:
    hits: list[str] = []
    for previous, current in zip(ordered, ordered[1:], strict=False):
        days = (current.timestamp - previous.timestamp).days
        if days > max_days:
            hits.append(f"{previous.timestamp.date()} to {current.timestamp.date()} ({days}d)")
    return _issue(
        "calendar_gap",
        QualityDimension.COMPLETENESS,
        QualityStatus.WARNING,
        f"gap(s) longer than {max_days} calendar days",
        hits,
    )


def _staleness_issues(last: Candle, now: datetime, max_days: int) -> list[QualityIssue]:
    age = (now - last.timestamp).days
    hits = [f"last bar {last.timestamp.date()} is {age}d old"] if age > max_days else []
    return _issue(
        "stale_series",
        QualityDimension.FRESHNESS,
        QualityStatus.WARNING,
        f"stale series (last bar older than {max_days} days)",
        hits,
    )
