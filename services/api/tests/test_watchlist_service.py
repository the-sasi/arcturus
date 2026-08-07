from datetime import UTC, datetime
from uuid import UUID, uuid4

from arcturus_api.application.watchlist.service import WatchlistService
from arcturus_api.domain.market.models import Symbol
from arcturus_api.domain.watchlist.errors import (
    DuplicateWatchlistItemError,
    WatchlistNotFoundError,
)
from arcturus_api.domain.watchlist.models import Watchlist, WatchlistItem
from arcturus_api.domain.watchlist.ports import WatchlistRepository


class InMemoryWatchlistRepository(WatchlistRepository):
    def __init__(self) -> None:
        self._lists: dict[UUID, Watchlist] = {}

    async def list_all(self) -> list[Watchlist]:
        return list(self._lists.values())

    async def get(self, watchlist_id: UUID) -> Watchlist:
        if watchlist_id not in self._lists:
            raise WatchlistNotFoundError(watchlist_id)
        return self._lists[watchlist_id]

    async def create(self, name: str) -> Watchlist:
        watchlist = Watchlist(id=uuid4(), name=name, created_at=datetime.now(UTC), items=[])
        self._lists[watchlist.id] = watchlist
        return watchlist

    async def delete(self, watchlist_id: UUID) -> None:
        if self._lists.pop(watchlist_id, None) is None:
            raise WatchlistNotFoundError(watchlist_id)

    async def add_item(self, watchlist_id: UUID, symbol: Symbol) -> Watchlist:
        current = await self.get(watchlist_id)
        if any(item.symbol == symbol for item in current.items):
            raise DuplicateWatchlistItemError(str(symbol))
        updated = current.model_copy(
            update={
                "items": [
                    *current.items,
                    WatchlistItem(symbol=symbol, added_at=datetime.now(UTC)),
                ]
            }
        )
        self._lists[watchlist_id] = updated
        return updated

    async def remove_item(self, watchlist_id: UUID, symbol: Symbol) -> Watchlist:
        current = await self.get(watchlist_id)
        updated = current.model_copy(
            update={"items": [item for item in current.items if item.symbol != symbol]}
        )
        self._lists[watchlist_id] = updated
        return updated


class TestWatchlistService:
    async def test_create_strips_name(self) -> None:
        service = WatchlistService(InMemoryWatchlistRepository())
        watchlist = await service.create_watchlist("  Swing Ideas  ")
        assert watchlist.name == "Swing Ideas"

    async def test_add_symbol_normalises(self) -> None:
        service = WatchlistService(InMemoryWatchlistRepository())
        watchlist = await service.create_watchlist("Test")
        updated = await service.add_symbol(watchlist.id, "nse:tcs")
        assert str(updated.items[0].symbol) == "NSE:TCS"

    async def test_remove_symbol(self) -> None:
        service = WatchlistService(InMemoryWatchlistRepository())
        watchlist = await service.create_watchlist("Test")
        await service.add_symbol(watchlist.id, "NSE:TCS")
        updated = await service.remove_symbol(watchlist.id, "NSE:TCS")
        assert updated.items == []
