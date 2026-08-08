"""Instrument directory domain: browsing/searching the listed universe."""

from pydantic import BaseModel, ConfigDict

from arcturus_api.domain.market.models import Instrument, Quote


class InstrumentPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Instrument]
    total: int
    limit: int
    offset: int


class DirectorySyncResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    fetched: int
    upserted: int


class MoversSnapshot(BaseModel):
    """Top gainers/losers across a quote universe (curated until Phase 2)."""

    model_config = ConfigDict(frozen=True)

    gainers: list[Quote]
    losers: list[Quote]
    universe_size: int
    quoted: int
    advancing: int
    declining: int
