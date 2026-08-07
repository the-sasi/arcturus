"""Watchlist domain errors."""

from uuid import UUID


class WatchlistError(Exception):
    """Base error for watchlist operations."""


class WatchlistNotFoundError(WatchlistError):
    def __init__(self, watchlist_id: UUID) -> None:
        self.watchlist_id = watchlist_id
        super().__init__(f"Watchlist not found: {watchlist_id}")


class WatchlistItemNotFoundError(WatchlistError):
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Symbol not in watchlist: {symbol}")


class DuplicateWatchlistNameError(WatchlistError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"A watchlist named '{name}' already exists")


class DuplicateWatchlistItemError(WatchlistError):
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Symbol already in watchlist: {symbol}")
