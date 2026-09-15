"""Deterministic identity linking: decide how listing rows change the entity graph.

Pure function over (validated listings, currently active identifiers). Rules:

1. Unknown symbol and unknown ISIN            -> create a company
2. Symbol and ISIN already on the same company -> refresh observation
3. Known ISIN, new symbol                      -> ISIN proves identity: the
   symbol was renamed; add it, deactivate the old one (history kept)
4. Known symbol, new or foreign ISIN           -> NOT provable (face-value
   change? symbol reuse?) -> record a conflict, change nothing
"""

from uuid import UUID

from arcturus_api.domain.data.conflicts import ConflictType, NewConflict
from arcturus_api.domain.data.sources import preferred_source
from arcturus_api.domain.identity.models import (
    LISTING_SCHEMES,
    CompanyUpdate,
    IdentifierKey,
    IdentifierScheme,
    IdentitySyncPlan,
    ListingIdentity,
    NewCompany,
)


def plan_listing_sync(
    listings: list[ListingIdentity],
    active: dict[IdentifierKey, UUID],
    source_id: str,
) -> IdentitySyncPlan:
    owned: dict[UUID, dict[IdentifierScheme, list[str]]] = {}
    for key, company_id in active.items():
        owned.setdefault(company_id, {}).setdefault(key.scheme, []).append(key.value)

    creates: list[NewCompany] = []
    updates: list[CompanyUpdate] = []
    conflicts: list[NewConflict] = []

    for listing in listings:
        scheme = LISTING_SCHEMES.get(listing.symbol.exchange)
        if scheme is None:
            raise ValueError(f"no identity scheme for exchange {listing.symbol.exchange}")
        symbol_key = IdentifierKey(scheme=scheme, value=listing.symbol.ticker)
        isin_key = IdentifierKey(scheme=IdentifierScheme.ISIN, value=listing.isin)
        by_symbol = active.get(symbol_key)
        by_isin = active.get(isin_key)

        if by_symbol is None and by_isin is None:
            creates.append(
                NewCompany(name=listing.name, country="IN", identifiers=[isin_key, symbol_key])
            )
        elif by_symbol is not None and by_symbol == by_isin:
            updates.append(
                CompanyUpdate(company_id=by_symbol, name=listing.name, touch=[isin_key, symbol_key])
            )
        elif by_isin is not None and by_symbol is None:
            previous = owned.get(by_isin, {}).get(scheme, [])
            updates.append(
                CompanyUpdate(
                    company_id=by_isin,
                    name=listing.name,
                    touch=[isin_key],
                    add=[symbol_key],
                    deactivate=[IdentifierKey(scheme=scheme, value=value) for value in previous],
                )
            )
        else:
            assert by_symbol is not None
            linked_isins = sorted(owned.get(by_symbol, {}).get(IdentifierScheme.ISIN, []))
            reason = (
                f"ISIN {listing.isin} is already linked to a different company"
                if by_isin is not None
                else f"known symbol now reports ISIN {listing.isin} (possible face-value "
                "change or symbol reuse) — not provable from identifiers alone"
            )
            conflicts.append(
                NewConflict(
                    conflict_type=ConflictType.IDENTIFIER_MISMATCH,
                    entity_id=by_symbol,
                    subject=str(symbol_key),
                    metric="isin",
                    source_a_id=source_id,
                    value_a=", ".join(linked_isins) or None,
                    source_b_id=source_id,
                    value_b=listing.isin,
                    preferred_source_id=preferred_source(source_id, source_id),
                    reason=reason,
                )
            )

    return IdentitySyncPlan(creates=creates, updates=updates, conflicts=conflicts)
