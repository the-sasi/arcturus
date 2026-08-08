"""Integration tests for the instrument repository, against in-memory SQLite."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from arcturus_api.domain.market.models import AssetClass, Exchange, Instrument, Symbol
from arcturus_api.infrastructure.db.engine import build_session_factory
from arcturus_api.infrastructure.db.instrument_repository import SqlAlchemyInstrumentRepository
from arcturus_api.infrastructure.db.orm import Base


def make(exchange: Exchange, ticker: str, name: str) -> Instrument:
    return Instrument(
        symbol=Symbol(exchange=exchange, ticker=ticker),
        name=name,
        asset_class=AssetClass.EQUITY,
        currency="INR" if exchange in (Exchange.NSE, Exchange.BSE) else "USD",
    )


@pytest.fixture
async def repository() -> AsyncIterator[SqlAlchemyInstrumentRepository]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    repo = SqlAlchemyInstrumentRepository(build_session_factory(engine))
    await repo.upsert_many(
        [
            make(Exchange.NSE, "RELIANCE", "Reliance Industries Limited"),
            make(Exchange.NSE, "TCS", "Tata Consultancy Services Limited"),
            make(Exchange.NSE, "TATAMOTORS", "Tata Motors Limited"),
            make(Exchange.NASDAQ, "AAPL", "Apple Inc."),
        ]
    )
    yield repo
    await engine.dispose()


class TestInstrumentRepository:
    async def test_browse_all_ordered(self, repository: SqlAlchemyInstrumentRepository) -> None:
        items, total = await repository.search(None, None, limit=10, offset=0)
        assert total == 4
        assert [str(item.symbol) for item in items][0] == "NASDAQ:AAPL"

    async def test_search_by_name_fragment(
        self, repository: SqlAlchemyInstrumentRepository
    ) -> None:
        items, total = await repository.search("tata", None, limit=10, offset=0)
        assert total == 2
        assert all("Tata" in item.name for item in items)

    async def test_filter_by_exchange(self, repository: SqlAlchemyInstrumentRepository) -> None:
        _, total = await repository.search(None, Exchange.NSE, limit=10, offset=0)
        assert total == 3

    async def test_pagination(self, repository: SqlAlchemyInstrumentRepository) -> None:
        items, total = await repository.search(None, None, limit=2, offset=2)
        assert total == 4
        assert len(items) == 2

    async def test_upsert_updates_existing(
        self, repository: SqlAlchemyInstrumentRepository
    ) -> None:
        written = await repository.upsert_many(
            [make(Exchange.NSE, "RELIANCE", "Reliance Industries Ltd (Renamed)")]
        )
        assert written == 1
        items, total = await repository.search("renamed", None, limit=10, offset=0)
        assert total == 1
        _, grand_total = await repository.search(None, None, limit=10, offset=0)
        assert grand_total == 4  # updated, not duplicated
