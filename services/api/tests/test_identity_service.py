"""Entity resolution end to end against in-memory SQLite: idempotency, history,
conflicts, point-in-time resolution and provenance."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from arcturus_api.application.identity.service import EntityResolutionService
from arcturus_api.domain.data.conflicts import ResolutionStatus
from arcturus_api.domain.data.sources import SourceType, UnknownSourceError
from arcturus_api.domain.identity.models import (
    EntityNotFoundError,
    IdentifierScheme,
    InvalidIdentifierError,
)
from arcturus_api.domain.market.models import AssetClass, Exchange, Instrument, Symbol
from arcturus_api.domain.quality.models import QualityStatus
from arcturus_api.infrastructure.db.engine import build_session_factory
from arcturus_api.infrastructure.db.identity_repository import SqlAlchemyCompanyIdentityRepository
from arcturus_api.infrastructure.db.orm import Base

SOURCE = "nse_archives"
RELIANCE_ISIN = "INE002A01018"
TCS_ISIN = "INE467B01029"
T0 = datetime(2026, 9, 1, tzinfo=UTC)
T1 = datetime(2026, 9, 15, tzinfo=UTC)


def nse(ticker: str, isin: str | None, name: str | None = None) -> Instrument:
    return Instrument(
        symbol=Symbol(exchange=Exchange.NSE, ticker=ticker),
        name=name or f"{ticker} Limited",
        asset_class=AssetClass.EQUITY,
        currency="INR",
        isin=isin,
    )


BASE = [
    nse("RELIANCE", RELIANCE_ISIN, "Reliance Industries Limited"),
    nse("TCS", TCS_ISIN, "Tata Consultancy Services Limited"),
]


@pytest.fixture
async def service() -> AsyncIterator[EntityResolutionService]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield EntityResolutionService(
        SqlAlchemyCompanyIdentityRepository(build_session_factory(engine))
    )
    await engine.dispose()


class TestIngestion:
    async def test_first_sync_links_symbol_and_isin_to_one_company(
        self, service: EntityResolutionService
    ) -> None:
        result = await service.ingest_listings(SOURCE, BASE, T0)
        assert result.applied
        assert (result.companies_created, result.identifiers_added) == (2, 4)

        by_symbol = await service.resolve("NSE:RELIANCE")
        by_isin = await service.resolve(RELIANCE_ISIN)
        assert by_symbol.company_id == by_isin.company_id
        assert by_symbol.name == "Reliance Industries Limited"
        assert by_symbol.canonical_symbols == ["NSE:RELIANCE"]
        assert {(item.scheme, item.value) for item in by_symbol.identifiers} == {
            (IdentifierScheme.ISIN, RELIANCE_ISIN),
            (IdentifierScheme.NSE_SYMBOL, "RELIANCE"),
        }

    async def test_every_identifier_traces_to_its_source(
        self, service: EntityResolutionService
    ) -> None:
        await service.ingest_listings(SOURCE, BASE, T0)
        identity = await service.resolve("NSE:TCS")
        for identifier in identity.identifiers:
            assert identifier.provenance.source_id == SOURCE
            assert identifier.provenance.source_type == SourceType.EXCHANGE
            assert identifier.provenance.entity_id == str(identity.company_id)

    async def test_resync_is_idempotent(self, service: EntityResolutionService) -> None:
        await service.ingest_listings(SOURCE, BASE, T0)
        again = await service.ingest_listings(SOURCE, BASE, T1)
        assert (again.companies_created, again.identifiers_added) == (0, 0)
        assert again.companies_updated == 2
        assert again.conflicts_opened == 0
        identity = await service.resolve("NSE:TCS")
        assert len(identity.identifiers) == 2
        assert all(item.last_seen_at > item.first_seen_at for item in identity.identifiers)

    async def test_symbol_rename_proven_by_isin_keeps_history(
        self, service: EntityResolutionService
    ) -> None:
        await service.ingest_listings(SOURCE, [nse("OLDNAME", RELIANCE_ISIN)], T0)
        result = await service.ingest_listings(SOURCE, [nse("NEWNAME", RELIANCE_ISIN)], T1)
        assert (result.identifiers_added, result.identifiers_deactivated) == (1, 1)

        identity = await service.resolve("NSE:NEWNAME")
        assert identity.canonical_symbols == ["NSE:NEWNAME"]
        old = next(item for item in identity.identifiers if item.value == "OLDNAME")
        assert not old.active
        with pytest.raises(EntityNotFoundError):
            await service.resolve("NSE:OLDNAME")

    async def test_unprovable_isin_change_is_recorded_not_applied(
        self, service: EntityResolutionService
    ) -> None:
        await service.ingest_listings(SOURCE, [nse("RELIANCE", RELIANCE_ISIN)], T0)
        first = await service.ingest_listings(SOURCE, [nse("RELIANCE", TCS_ISIN)], T1)
        assert (first.conflicts_opened, first.identifiers_added) == (1, 0)

        again = await service.ingest_listings(
            SOURCE, [nse("RELIANCE", TCS_ISIN)], T1 + timedelta(days=1)
        )
        assert (again.conflicts_opened, again.conflicts_redetected) == (0, 1)

        page = await service.list_conflicts(ResolutionStatus.OPEN)
        assert page.total == 1
        conflict = page.items[0]
        identity = await service.resolve("NSE:RELIANCE")
        assert conflict.entity_id == identity.company_id
        assert (conflict.value_a, conflict.value_b) == (RELIANCE_ISIN, TCS_ISIN)
        assert identity.open_conflicts == 1
        assert [
            item.value for item in identity.identifiers if item.scheme == IdentifierScheme.ISIN
        ] == [RELIANCE_ISIN]
        with pytest.raises(EntityNotFoundError):
            await service.resolve(TCS_ISIN)

    async def test_batch_failing_quality_writes_nothing(
        self, service: EntityResolutionService
    ) -> None:
        batch = [nse("GOOD", RELIANCE_ISIN)] + [nse(f"BAD{index}", None) for index in range(5)]
        result = await service.ingest_listings(SOURCE, batch, T0)
        assert not result.applied
        assert result.quality.status == QualityStatus.INVALID
        with pytest.raises(EntityNotFoundError):
            await service.resolve("NSE:GOOD")

    async def test_evidence_must_come_from_a_registered_source(
        self, service: EntityResolutionService
    ) -> None:
        with pytest.raises(UnknownSourceError):
            await service.ingest_listings("scraped_somewhere", BASE, T0)

    async def test_vendor_tickers_are_not_identifiers(
        self, service: EntityResolutionService
    ) -> None:
        with pytest.raises(InvalidIdentifierError):
            await service.resolve("RELIANCE.NS")


class TestPointInTime:
    async def test_identifiers_are_unavailable_before_first_observation(
        self, service: EntityResolutionService
    ) -> None:
        await service.ingest_listings(SOURCE, [nse("OLDNAME", RELIANCE_ISIN)], T0)
        await service.ingest_listings(SOURCE, [nse("NEWNAME", RELIANCE_ISIN)], T1)

        with pytest.raises(EntityNotFoundError):
            await service.resolve("NSE:OLDNAME", as_of=T0 - timedelta(days=1))

        at_t0 = await service.resolve("NSE:OLDNAME", as_of=T0)
        assert at_t0.canonical_symbols == ["NSE:OLDNAME"]
        assert "NEWNAME" not in {item.value for item in at_t0.identifiers}  # not yet known at T0

        with pytest.raises(EntityNotFoundError):
            await service.resolve("NSE:NEWNAME", as_of=T0)
        assert (await service.resolve("NSE:NEWNAME")).company_id == at_t0.company_id
