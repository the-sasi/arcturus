"""Integration tests for the SQLAlchemy repository, against in-memory SQLite."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from arcturus_api.domain.market.models import Symbol
from arcturus_api.domain.watchlist.errors import (
    DuplicateWatchlistItemError,
    DuplicateWatchlistNameError,
    WatchlistItemNotFoundError,
    WatchlistNotFoundError,
)
from arcturus_api.infrastructure.db.engine import build_session_factory
from arcturus_api.infrastructure.db.orm import Base
from arcturus_api.infrastructure.db.watchlist_repository import SqlAlchemyWatchlistRepository


@pytest.fixture
async def repository() -> AsyncIterator[SqlAlchemyWatchlistRepository]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield SqlAlchemyWatchlistRepository(build_session_factory(engine))
    await engine.dispose()


class TestSqlAlchemyWatchlistRepository:
    async def test_create_and_get(self, repository: SqlAlchemyWatchlistRepository) -> None:
        created = await repository.create("Momentum")
        fetched = await repository.get(created.id)
        assert fetched.name == "Momentum"
        assert fetched.items == []

    async def test_duplicate_name_raises(self, repository: SqlAlchemyWatchlistRepository) -> None:
        await repository.create("Momentum")
        with pytest.raises(DuplicateWatchlistNameError):
            await repository.create("Momentum")

    async def test_get_missing_raises(self, repository: SqlAlchemyWatchlistRepository) -> None:
        with pytest.raises(WatchlistNotFoundError):
            await repository.get(uuid4())

    async def test_add_and_remove_item(self, repository: SqlAlchemyWatchlistRepository) -> None:
        watchlist = await repository.create("Swing")
        symbol = Symbol.parse("NSE:RELIANCE")

        updated = await repository.add_item(watchlist.id, symbol)
        assert [str(item.symbol) for item in updated.items] == ["NSE:RELIANCE"]

        emptied = await repository.remove_item(watchlist.id, symbol)
        assert emptied.items == []

    async def test_duplicate_item_raises(self, repository: SqlAlchemyWatchlistRepository) -> None:
        watchlist = await repository.create("Swing")
        symbol = Symbol.parse("NSE:RELIANCE")
        await repository.add_item(watchlist.id, symbol)
        with pytest.raises(DuplicateWatchlistItemError):
            await repository.add_item(watchlist.id, symbol)

    async def test_remove_missing_item_raises(
        self, repository: SqlAlchemyWatchlistRepository
    ) -> None:
        watchlist = await repository.create("Swing")
        with pytest.raises(WatchlistItemNotFoundError):
            await repository.remove_item(watchlist.id, Symbol.parse("NSE:TCS"))

    async def test_delete_cascades(self, repository: SqlAlchemyWatchlistRepository) -> None:
        watchlist = await repository.create("Doomed")
        await repository.add_item(watchlist.id, Symbol.parse("NASDAQ:AAPL"))
        await repository.delete(watchlist.id)
        assert await repository.list_all() == []
