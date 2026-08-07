"""Watchlist domain models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from arcturus_api.domain.market.models import Symbol


class WatchlistItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: Symbol
    added_at: datetime


class Watchlist(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    created_at: datetime
    items: list[WatchlistItem]
