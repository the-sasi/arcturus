from decimal import Decimal

from arcturus_api.domain.market.models import Symbol
from arcturus_api.infrastructure.providers.yahoo.parsers import (
    parse_fundamentals,
    parse_news_item,
    parse_profile,
)

RELIANCE = Symbol.parse("NSE:RELIANCE")

SAMPLE_INFO = {
    "longName": "Reliance Industries Limited",
    "sector": "Energy",
    "industry": "Oil & Gas Refining & Marketing",
    "country": "India",
    "website": "https://www.ril.com",
    "fullTimeEmployeers_typo_ignored": None,
    "fullTimeEmployees": 347000,
    "longBusinessSummary": "Reliance Industries Limited engages in...",
    "currency": "INR",
    "marketCap": 18_000_000_000_000,
    "trailingPE": 27.5,
    "forwardPE": 22.1,
    "priceToBook": 2.3,
    "trailingEps": 48.51,
    "dividendYield": 0.0035,
    "beta": 0.55,
    "fiftyTwoWeekHigh": 1608.8,
    "fiftyTwoWeekLow": 1115.55,
    "averageVolume": 11_500_000,
    "totalRevenue": 9_740_000_000_000,
    "profitMargins": 0.0715,
    "returnOnEquity": 0.0842,
    "debtToEquity": 36.7,
    "recommendationKey": "buy",
    "targetMeanPrice": 1650.0,
}


class TestParseProfile:
    def test_full_profile(self) -> None:
        profile = parse_profile(RELIANCE, SAMPLE_INFO)
        assert profile.name == "Reliance Industries Limited"
        assert profile.sector == "Energy"
        assert profile.employees == 347000

    def test_empty_info_falls_back_to_ticker(self) -> None:
        profile = parse_profile(RELIANCE, {})
        assert profile.name == "RELIANCE"
        assert profile.sector is None


class TestParseFundamentals:
    def test_typed_fields(self) -> None:
        fundamentals = parse_fundamentals(RELIANCE, SAMPLE_INFO)
        assert fundamentals.currency == "INR"
        assert fundamentals.market_cap == 18_000_000_000_000
        assert fundamentals.trailing_pe == Decimal("27.5")
        assert fundamentals.profit_margin == Decimal("0.0715")

    def test_extras_carry_unpromoted_fields(self) -> None:
        fundamentals = parse_fundamentals(RELIANCE, SAMPLE_INFO)
        assert fundamentals.extras["recommendationKey"] == "buy"
        assert fundamentals.extras["targetMeanPrice"] == 1650.0

    def test_garbage_values_become_none(self) -> None:
        fundamentals = parse_fundamentals(
            RELIANCE, {"trailingPE": "Infinity", "beta": None, "marketCap": "n/a"}
        )
        assert fundamentals.trailing_pe is None
        assert fundamentals.beta is None
        assert fundamentals.market_cap is None


class TestParseNewsItem:
    def test_legacy_flat_shape(self) -> None:
        article = parse_news_item(
            {
                "title": "RIL announces Q1 results",
                "publisher": "Business Standard",
                "link": "https://example.com/a",
                "providerPublishTime": 1754550000,
            }
        )
        assert article is not None
        assert article.publisher == "Business Standard"
        assert article.published_at is not None

    def test_nested_content_shape(self) -> None:
        article = parse_news_item(
            {
                "id": "abc",
                "content": {
                    "title": "Reliance expands retail arm",
                    "pubDate": "2026-08-07T10:00:00Z",
                    "summary": "The company said...",
                    "provider": {"displayName": "Reuters"},
                    "canonicalUrl": {"url": "https://example.com/b"},
                },
            }
        )
        assert article is not None
        assert article.publisher == "Reuters"
        assert article.url == "https://example.com/b"
        assert article.summary == "The company said..."

    def test_untitled_item_dropped(self) -> None:
        assert parse_news_item({"content": {"summary": "no title"}}) is None
