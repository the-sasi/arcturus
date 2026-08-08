"""Pure parsing of Yahoo vendor payloads into domain models.

Kept free of I/O so the messy vendor shapes are unit-testable with fixtures.
Yahoo's `info` dict and news payloads vary by instrument and yfinance version;
every field access here is defensive.
"""

import math
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from arcturus_api.domain.market.fundamentals import CompanyProfile, Fundamentals, NewsArticle
from arcturus_api.domain.market.models import Symbol

# Vendor fields worth carrying for the future decision engine, beyond the
# typed Fundamentals columns.
_EXTRA_KEYS = (
    "recommendationKey",
    "targetMeanPrice",
    "earningsGrowth",
    "revenueGrowth",
    "grossMargins",
    "operatingMargins",
    "bookValue",
    "priceToSalesTrailing12Months",
    "fiftyDayAverage",
    "twoHundredDayAverage",
    "sharesOutstanding",
    "heldPercentInstitutions",
)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        return Decimal(str(round(number, 6)))
    except (ValueError, TypeError, InvalidOperation):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def parse_profile(symbol: Symbol, info: dict[str, Any]) -> CompanyProfile:
    return CompanyProfile(
        symbol=symbol,
        name=_str_or_none(info.get("longName"))
        or _str_or_none(info.get("shortName"))
        or symbol.ticker,
        sector=_str_or_none(info.get("sector")),
        industry=_str_or_none(info.get("industry")),
        country=_str_or_none(info.get("country")),
        website=_str_or_none(info.get("website")),
        employees=_int_or_none(info.get("fullTimeEmployees")),
        summary=_str_or_none(info.get("longBusinessSummary")),
    )


def parse_fundamentals(symbol: Symbol, info: dict[str, Any]) -> Fundamentals:
    return Fundamentals(
        symbol=symbol,
        currency=_str_or_none(info.get("currency")),
        market_cap=_int_or_none(info.get("marketCap")),
        trailing_pe=_decimal_or_none(info.get("trailingPE")),
        forward_pe=_decimal_or_none(info.get("forwardPE")),
        price_to_book=_decimal_or_none(info.get("priceToBook")),
        eps_trailing=_decimal_or_none(info.get("trailingEps")),
        dividend_yield=_decimal_or_none(info.get("dividendYield")),
        beta=_decimal_or_none(info.get("beta")),
        fifty_two_week_high=_decimal_or_none(info.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_decimal_or_none(info.get("fiftyTwoWeekLow")),
        average_volume=_int_or_none(info.get("averageVolume")),
        revenue=_int_or_none(info.get("totalRevenue")),
        profit_margin=_decimal_or_none(info.get("profitMargins")),
        return_on_equity=_decimal_or_none(info.get("returnOnEquity")),
        debt_to_equity=_decimal_or_none(info.get("debtToEquity")),
        as_of=datetime.now(UTC),
        extras={key: info[key] for key in _EXTRA_KEYS if info.get(key) is not None},
    )


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def parse_news_item(raw: dict[str, Any]) -> NewsArticle | None:
    """Handle both legacy flat and current nested `content` news shapes."""
    nested = raw.get("content")
    content: dict[str, Any] = nested if isinstance(nested, dict) else raw

    title = _str_or_none(content.get("title"))
    if title is None:
        return None

    publisher = _str_or_none(content.get("publisher"))
    if publisher is None:
        provider = content.get("provider")
        if isinstance(provider, dict):
            publisher = _str_or_none(provider.get("displayName"))

    url = _str_or_none(content.get("link"))
    if url is None:
        canonical = content.get("canonicalUrl")
        if isinstance(canonical, dict):
            url = _str_or_none(canonical.get("url"))

    published_at = _parse_timestamp(content.get("providerPublishTime") or content.get("pubDate"))

    return NewsArticle(
        title=title,
        publisher=publisher,
        url=url,
        published_at=published_at,
        summary=_str_or_none(content.get("summary")),
        image_url=_extract_thumbnail(content),
    )


def _extract_thumbnail(content: dict[str, Any]) -> str | None:
    thumbnail = content.get("thumbnail")
    if not isinstance(thumbnail, dict):
        return None
    resolutions = thumbnail.get("resolutions")
    if not isinstance(resolutions, list) or not resolutions:
        return _str_or_none(thumbnail.get("originalUrl"))
    # Prefer the smallest rendition ≥200px wide to keep list views light.
    candidates = [
        item for item in resolutions if isinstance(item, dict) and isinstance(item.get("url"), str)
    ]
    if not candidates:
        return None
    sized = sorted(
        (item for item in candidates if isinstance(item.get("width"), int)),
        key=lambda item: item["width"],
    )
    for item in sized:
        if item["width"] >= 200:
            return str(item["url"])
    return str((sized[-1] if sized else candidates[0])["url"])
