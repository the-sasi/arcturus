"""Fundamental and company data domain models.

Curated, typed fields for what the platform reasons about; everything else the
vendor returns is preserved in ``extras`` so no data is silently dropped.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from arcturus_api.domain.market.models import Symbol


class CompanyProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: Symbol
    name: str
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    website: str | None = None
    employees: int | None = None
    summary: str | None = None


class Fundamentals(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: Symbol
    currency: str | None = None
    market_cap: int | None = None
    trailing_pe: Decimal | None = None
    forward_pe: Decimal | None = None
    price_to_book: Decimal | None = None
    eps_trailing: Decimal | None = None
    dividend_yield: Decimal | None = None
    beta: Decimal | None = None
    fifty_two_week_high: Decimal | None = None
    fifty_two_week_low: Decimal | None = None
    average_volume: int | None = None
    revenue: int | None = None
    profit_margin: Decimal | None = None
    return_on_equity: Decimal | None = None
    debt_to_equity: Decimal | None = None
    as_of: datetime
    # Vendor fields not yet promoted to typed columns
    extras: dict[str, Any] = Field(default_factory=dict)


class NewsArticle(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    publisher: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    summary: str | None = None
