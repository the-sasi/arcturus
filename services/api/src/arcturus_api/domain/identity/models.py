"""Company identity models (shared data platform).

A company is a surrogate-keyed entity. Tickers get renamed and ISINs change on
face-value changes, so neither can be the primary key; both are identifiers
with an observation history. ISIN is the cross-source identity key: two
listings are the same entity only when an identifier proves it — never on a
name match.

Point-in-time semantics: ``first_seen_at`` is when Arcturus first observed an
identifier (its availability date), ``last_seen_at`` the latest observation.
Arcturus cannot know identifiers from before its first sync.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from arcturus_api.domain.data.conflicts import NewConflict
from arcturus_api.domain.data.provenance import DataProvenance
from arcturus_api.domain.market.models import Exchange, Symbol
from arcturus_api.domain.quality.models import DataQualityReport


class IdentifierScheme(StrEnum):
    ISIN = "isin"
    NSE_SYMBOL = "nse_symbol"
    BSE_CODE = "bse_code"  # no source ingested yet
    CIN = "cin"  # no source ingested yet


# Exchanges whose listing symbol is an identity scheme
LISTING_SCHEMES: dict[Exchange, IdentifierScheme] = {Exchange.NSE: IdentifierScheme.NSE_SYMBOL}


class IdentifierKey(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme: IdentifierScheme
    value: str

    def __str__(self) -> str:
        return f"{self.scheme.name}:{self.value}"


class CompanyIdentifier(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme: IdentifierScheme
    value: str
    active: bool
    first_seen_at: datetime
    last_seen_at: datetime
    provenance: DataProvenance


class CompanyIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: UUID
    name: str
    country: str
    identifiers: list[CompanyIdentifier]
    # Active listings in the platform's canonical EXCHANGE:TICKER form
    canonical_symbols: list[str]
    open_conflicts: int


class ListingIdentity(BaseModel):
    """One validated listing row that may be used as identity evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: Symbol
    isin: str
    name: str


class NewCompany(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    country: str
    identifiers: list[IdentifierKey]


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: UUID
    name: str
    touch: list[IdentifierKey]  # observed again: refresh last_seen_at
    add: list[IdentifierKey] = []  # newly proven identifiers
    deactivate: list[IdentifierKey] = []  # superseded (history kept)


class IdentitySyncPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    creates: list[NewCompany]
    updates: list[CompanyUpdate]
    conflicts: list[NewConflict]


class IdentitySyncResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    applied: bool  # False when the batch failed quality checks and nothing was written
    quality: DataQualityReport
    companies_created: int = 0
    companies_updated: int = 0
    identifiers_added: int = 0
    identifiers_deactivated: int = 0
    conflicts_opened: int = 0
    conflicts_redetected: int = 0


class InvalidIdentifierError(Exception):
    def __init__(self, raw: str) -> None:
        super().__init__(
            f"Unrecognised identifier '{raw}'. Use NSE:SYMBOL, BSE:SCRIPCODE or an ISIN."
        )
        self.raw = raw


class EntityNotFoundError(Exception):
    def __init__(self, raw: str) -> None:
        super().__init__(f"No company known for identifier '{raw}'")
        self.raw = raw
