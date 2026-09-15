"""Listing validation before rows become identity evidence."""

from datetime import UTC, datetime

from arcturus_api.domain.identity.identifiers import isin_check_digit
from arcturus_api.domain.market.models import AssetClass, Exchange, Instrument, Symbol
from arcturus_api.domain.quality.listings import assess_listings
from arcturus_api.domain.quality.models import QualityStatus

NOW = datetime(2026, 9, 15, tzinfo=UTC)
SOURCE = "nse_archives"


def make_isin(number: int) -> str:
    payload = f"INE{number:06d}01"
    return f"{payload}{isin_check_digit(payload)}"


def listing(ticker: str, isin: str | None) -> Instrument:
    return Instrument(
        symbol=Symbol(exchange=Exchange.NSE, ticker=ticker),
        name=f"{ticker} Limited",
        asset_class=AssetClass.EQUITY,
        currency="INR",
        isin=isin,
    )


def clean_batch(size: int) -> list[Instrument]:
    return [listing(f"CO{index}", make_isin(index)) for index in range(size)]


class TestListingQuality:
    def test_clean_listing_is_valid(self) -> None:
        report, accepted = assess_listings(clean_batch(20), SOURCE, NOW)
        assert report.status == QualityStatus.VALID
        assert len(accepted) == 20

    def test_missing_isin_rejects_row_with_warning(self) -> None:
        batch = clean_batch(20)
        batch[3] = listing("NOISIN", None)
        report, accepted = assess_listings(batch, SOURCE, NOW)
        assert report.status == QualityStatus.WARNING
        assert len(accepted) == 19
        assert {issue.check for issue in report.issues} == {"missing_isin"}

    def test_bad_check_digit_rejects_row(self) -> None:
        batch = clean_batch(20)
        batch[0] = listing("BADISIN", "INE002A01019")
        report, accepted = assess_listings(batch, SOURCE, NOW)
        assert "invalid_isin" in {issue.check for issue in report.issues}
        assert "BADISIN" not in {row.symbol.ticker for row in accepted}

    def test_shared_isin_rejects_every_sharing_row(self) -> None:
        batch = clean_batch(20)
        batch[1] = listing("TWIN", batch[0].isin)
        report, accepted = assess_listings(batch, SOURCE, NOW)
        assert len(accepted) == 18
        duplicate = next(issue for issue in report.issues if issue.check == "duplicate_identifier")
        assert duplicate.count == 2

    def test_isin_is_normalised(self) -> None:
        batch = clean_batch(19) + [listing("LOWER", " ine002a01018 ")]
        report, accepted = assess_listings(batch, SOURCE, NOW)
        assert report.status == QualityStatus.VALID
        assert accepted[-1].isin == "INE002A01018"

    def test_mass_rejection_is_invalid(self) -> None:
        batch = clean_batch(8) + [listing("X1", None), listing("X2", None)]
        report, _ = assess_listings(batch, SOURCE, NOW)
        assert report.status == QualityStatus.INVALID
        assert "rejected_share" in {issue.check for issue in report.issues}

    def test_empty_listing_is_invalid(self) -> None:
        report, accepted = assess_listings([], SOURCE, NOW)
        assert report.status == QualityStatus.INVALID
        assert accepted == []
