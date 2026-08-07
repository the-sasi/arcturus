"""Hexagonal port for watchlist persistence."""

from abc import ABC, abstractmethod
from uuid import UUID

from arcturus_api.domain.market.models import Symbol
from arcturus_api.domain.watchlist.models import Watchlist


class WatchlistRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[Watchlist]: ...

    @abstractmethod
    async def get(self, watchlist_id: UUID) -> Watchlist:
        """Raises WatchlistNotFoundError if absent."""

    @abstractmethod
    async def create(self, name: str) -> Watchlist:
        """Raises DuplicateWatchlistNameError on name collision."""

    @abstractmethod
    async def delete(self, watchlist_id: UUID) -> None:
        """Raises WatchlistNotFoundError if absent."""

    @abstractmethod
    async def add_item(self, watchlist_id: UUID, symbol: Symbol) -> Watchlist:
        """Raises WatchlistNotFoundError / DuplicateWatchlistItemError."""

    @abstractmethod
    async def remove_item(self, watchlist_id: UUID, symbol: Symbol) -> Watchlist:
        """Raises WatchlistNotFoundError if watchlist or item absent."""
