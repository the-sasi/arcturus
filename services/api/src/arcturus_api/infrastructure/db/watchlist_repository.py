"""SQLAlchemy implementation of the WatchlistRepository port."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from arcturus_api.domain.market.models import Symbol
from arcturus_api.domain.watchlist.errors import (
    DuplicateWatchlistItemError,
    DuplicateWatchlistNameError,
    WatchlistItemNotFoundError,
    WatchlistNotFoundError,
)
from arcturus_api.domain.watchlist.models import Watchlist, WatchlistItem
from arcturus_api.domain.watchlist.ports import WatchlistRepository
from arcturus_api.infrastructure.db.orm import WatchlistItemRow, WatchlistRow


def _to_domain(row: WatchlistRow) -> Watchlist:
    return Watchlist(
        id=row.id,
        name=row.name,
        created_at=row.created_at,
        items=[
            WatchlistItem(symbol=Symbol.parse(item.symbol), added_at=item.added_at)
            for item in row.items
        ],
    )


class SqlAlchemyWatchlistRepository(WatchlistRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def _get_row(self, session: AsyncSession, watchlist_id: UUID) -> WatchlistRow:
        row = await session.get(WatchlistRow, watchlist_id)
        if row is None:
            raise WatchlistNotFoundError(watchlist_id)
        return row

    async def list_all(self) -> list[Watchlist]:
        async with self._session_factory() as session:
            rows = await session.scalars(select(WatchlistRow).order_by(WatchlistRow.created_at))
            return [_to_domain(row) for row in rows]

    async def get(self, watchlist_id: UUID) -> Watchlist:
        async with self._session_factory() as session:
            return _to_domain(await self._get_row(session, watchlist_id))

    async def create(self, name: str) -> Watchlist:
        async with self._session_factory() as session:
            row = WatchlistRow(name=name)
            session.add(row)
            try:
                await session.commit()
            except IntegrityError as exc:
                raise DuplicateWatchlistNameError(name) from exc
            await session.refresh(row)
            return _to_domain(row)

    async def delete(self, watchlist_id: UUID) -> None:
        async with self._session_factory() as session:
            row = await self._get_row(session, watchlist_id)
            await session.delete(row)
            await session.commit()

    async def add_item(self, watchlist_id: UUID, symbol: Symbol) -> Watchlist:
        async with self._session_factory() as session:
            row = await self._get_row(session, watchlist_id)
            session.add(WatchlistItemRow(watchlist_id=row.id, symbol=str(symbol)))
            try:
                await session.commit()
            except IntegrityError as exc:
                raise DuplicateWatchlistItemError(str(symbol)) from exc
            await session.refresh(row, attribute_names=["items"])
            return _to_domain(row)

    async def remove_item(self, watchlist_id: UUID, symbol: Symbol) -> Watchlist:
        async with self._session_factory() as session:
            row = await self._get_row(session, watchlist_id)
            target = next((item for item in row.items if item.symbol == str(symbol)), None)
            if target is None:
                raise WatchlistItemNotFoundError(str(symbol))
            await session.delete(target)
            await session.commit()
            await session.refresh(row, attribute_names=["items"])
            return _to_domain(row)
