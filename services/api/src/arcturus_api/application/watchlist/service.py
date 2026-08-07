"""Watchlist use cases."""

from uuid import UUID

from arcturus_api.domain.market.models import Symbol
from arcturus_api.domain.watchlist.models import Watchlist
from arcturus_api.domain.watchlist.ports import WatchlistRepository


class WatchlistService:
    def __init__(self, repository: WatchlistRepository) -> None:
        self._repository = repository

    async def list_watchlists(self) -> list[Watchlist]:
        return await self._repository.list_all()

    async def get_watchlist(self, watchlist_id: UUID) -> Watchlist:
        return await self._repository.get(watchlist_id)

    async def create_watchlist(self, name: str) -> Watchlist:
        return await self._repository.create(name.strip())

    async def delete_watchlist(self, watchlist_id: UUID) -> None:
        await self._repository.delete(watchlist_id)

    async def add_symbol(self, watchlist_id: UUID, raw_symbol: str) -> Watchlist:
        return await self._repository.add_item(watchlist_id, Symbol.parse(raw_symbol))

    async def remove_symbol(self, watchlist_id: UUID, raw_symbol: str) -> Watchlist:
        return await self._repository.remove_item(watchlist_id, Symbol.parse(raw_symbol))
