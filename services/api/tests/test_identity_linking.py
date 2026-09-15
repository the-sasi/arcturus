"""Pure identity-linking rules: what is provable from identifiers, and what is a conflict."""

from uuid import uuid4

import pytest

from arcturus_api.domain.identity.linking import plan_listing_sync
from arcturus_api.domain.identity.models import IdentifierKey, IdentifierScheme, ListingIdentity
from arcturus_api.domain.market.models import Exchange, Symbol

SOURCE = "nse_archives"
RELIANCE_ISIN = "INE002A01018"
TCS_ISIN = "INE467B01029"
COMPANY_A = uuid4()
COMPANY_B = uuid4()


def row(ticker: str, isin: str) -> ListingIdentity:
    return ListingIdentity(
        symbol=Symbol(exchange=Exchange.NSE, ticker=ticker), isin=isin, name=f"{ticker} Limited"
    )


def symbol(value: str) -> IdentifierKey:
    return IdentifierKey(scheme=IdentifierScheme.NSE_SYMBOL, value=value)


def isin(value: str) -> IdentifierKey:
    return IdentifierKey(scheme=IdentifierScheme.ISIN, value=value)


class TestPlanListingSync:
    def test_unknown_listing_creates_company(self) -> None:
        plan = plan_listing_sync([row("RELIANCE", RELIANCE_ISIN)], {}, SOURCE)
        assert len(plan.creates) == 1
        assert set(plan.creates[0].identifiers) == {isin(RELIANCE_ISIN), symbol("RELIANCE")}
        assert plan.updates == []
        assert plan.conflicts == []

    def test_known_pair_is_refreshed(self) -> None:
        active = {symbol("RELIANCE"): COMPANY_A, isin(RELIANCE_ISIN): COMPANY_A}
        plan = plan_listing_sync([row("RELIANCE", RELIANCE_ISIN)], active, SOURCE)
        assert plan.creates == []
        update = plan.updates[0]
        assert update.company_id == COMPANY_A
        assert set(update.touch) == {symbol("RELIANCE"), isin(RELIANCE_ISIN)}
        assert update.add == []
        assert update.deactivate == []

    def test_symbol_rename_is_proven_by_isin(self) -> None:
        active = {symbol("OLDNAME"): COMPANY_A, isin(RELIANCE_ISIN): COMPANY_A}
        plan = plan_listing_sync([row("NEWNAME", RELIANCE_ISIN)], active, SOURCE)
        update = plan.updates[0]
        assert update.company_id == COMPANY_A
        assert update.add == [symbol("NEWNAME")]
        assert update.deactivate == [symbol("OLDNAME")]
        assert plan.conflicts == []

    def test_new_isin_for_known_symbol_is_a_conflict_not_a_change(self) -> None:
        active = {symbol("RELIANCE"): COMPANY_A, isin(RELIANCE_ISIN): COMPANY_A}
        plan = plan_listing_sync([row("RELIANCE", TCS_ISIN)], active, SOURCE)
        assert plan.creates == []
        assert plan.updates == []
        conflict = plan.conflicts[0]
        assert conflict.entity_id == COMPANY_A
        assert conflict.subject == "NSE_SYMBOL:RELIANCE"
        assert (conflict.value_a, conflict.value_b) == (RELIANCE_ISIN, TCS_ISIN)
        assert conflict.preferred_source_id is None  # same source: no authority preference
        assert "not provable" in conflict.reason

    def test_isin_owned_by_another_company_is_a_conflict(self) -> None:
        active = {
            symbol("RELIANCE"): COMPANY_A,
            isin(RELIANCE_ISIN): COMPANY_A,
            symbol("TCS"): COMPANY_B,
            isin(TCS_ISIN): COMPANY_B,
        }
        plan = plan_listing_sync([row("RELIANCE", TCS_ISIN)], active, SOURCE)
        assert plan.updates == []
        assert "different company" in plan.conflicts[0].reason

    def test_exchange_without_identity_scheme_is_rejected(self) -> None:
        listing = ListingIdentity(
            symbol=Symbol(exchange=Exchange.NASDAQ, ticker="AAPL"),
            isin="US0378331005",
            name="Apple",
        )
        with pytest.raises(ValueError, match="no identity scheme"):
            plan_listing_sync([listing], {}, SOURCE)
