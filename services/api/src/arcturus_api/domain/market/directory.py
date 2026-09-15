"""Instrument directory domain: browsing/searching the listed universe."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from arcturus_api.domain.identity.models import IdentitySyncResult
from arcturus_api.domain.market.models import Instrument, Quote


class InstrumentPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Instrument]
    total: int
    limit: int
    offset: int


class SyncStatus(StrEnum):
    OK = "ok"
    FAILED = "failed"


class DirectorySyncResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str  # data source registry id
    status: SyncStatus
    fetched: int
    upserted: int
    error: str | None = None
    # Identity evidence taken from the listing (None when the source carries no ISINs)
    identity: IdentitySyncResult | None = None


class MoversSnapshot(BaseModel):
    """Top gainers/losers across a quote universe (curated until Phase 2)."""

    model_config = ConfigDict(frozen=True)

    gainers: list[Quote]
    losers: list[Quote]
    universe_size: int
    quoted: int
    advancing: int
    declining: int
