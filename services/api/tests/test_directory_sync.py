"""Directory sync: failures are reported, and ISIN-bearing listings feed identity."""

from datetime import datetime

from arcturus_api.application.identity.service import EntityResolutionService
from arcturus_api.application.market.directory_service import InstrumentDirectoryService
from arcturus_api.domain.identity.models import IdentitySyncResult
from arcturus_api.domain.market.directory import SyncStatus
from arcturus_api.domain.market.errors import ProviderUnavailableError
from arcturus_api.domain.market.models import AssetClass, Exchange, Instrument, Symbol
from arcturus_api.domain.market.ports import InstrumentDirectoryProvider, InstrumentRepository
from arcturus_api.domain.quality.listings import assess_listings


class CountingRepository(InstrumentRepository):
    async def search(
        self, query: str | None, exchange: Exchange | None, limit: int, offset: int
    ) -> tuple[list[Instrument], int]:
        return [], 0

    async def upsert_many(self, instruments: list[Instrument]) -> int:
        return len(instruments)


class StaticProvider(InstrumentDirectoryProvider):
    def __init__(self, source_id: str, listings: list[Instrument]) -> None:
        self.name = source_id
        self.source_id = source_id
        self._listings = listings

    async def fetch_listings(self) -> list[Instrument]:
        return self._listings


class BrokenProvider(InstrumentDirectoryProvider):
    name = "nasdaqtrader"
    source_id = "nasdaqtrader"

    async def fetch_listings(self) -> list[Instrument]:
        raise ProviderUnavailableError(self.name, "HTTP 503")


class RecordingIdentity(EntityResolutionService):
    def __init__(self) -> None:
        self.sources: list[str] = []

    async def ingest_listings(
        self,
        source_id: str,
        listings: list[Instrument],
        observed_at: datetime | None = None,
    ) -> IdentitySyncResult:
        self.sources.append(source_id)
        report, _ = assess_listings(listings, source_id, datetime(2026, 9, 15))
        return IdentitySyncResult(source_id=source_id, applied=True, quality=report)


def instrument(exchange: Exchange, ticker: str, isin: str | None) -> Instrument:
    return Instrument(
        symbol=Symbol(exchange=exchange, ticker=ticker),
        name=ticker,
        asset_class=AssetClass.EQUITY,
        currency="INR",
        isin=isin,
    )


class TestDirectorySync:
    async def test_provider_failure_is_reported_not_silent(self) -> None:
        service = InstrumentDirectoryService(CountingRepository(), [BrokenProvider()])
        [result] = await service.sync_all()
        assert result.status == SyncStatus.FAILED
        assert result.error is not None and "HTTP 503" in result.error

    async def test_only_isin_bearing_listings_feed_identity(self) -> None:
        identity = RecordingIdentity()
        nse = StaticProvider("nse_archives", [instrument(Exchange.NSE, "RELIANCE", "INE002A01018")])
        us = StaticProvider("nasdaqtrader", [instrument(Exchange.NASDAQ, "AAPL", None)])
        service = InstrumentDirectoryService(CountingRepository(), [nse, us], identity=identity)

        nse_result, us_result = await service.sync_all()
        assert identity.sources == ["nse_archives"]
        assert nse_result.status == SyncStatus.OK
        assert nse_result.identity is not None
        assert us_result.identity is None
