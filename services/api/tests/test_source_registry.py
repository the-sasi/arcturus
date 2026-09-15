"""Source registry: trust hierarchy and honest access status are enforced in code."""

from datetime import date

import pytest
from pydantic import ValidationError

from arcturus_api.domain.data.sources import (
    SOURCES,
    TRUST_TIER,
    AuthorityLevel,
    DataSource,
    ImplementationStatus,
    LicenseStatus,
    SourceType,
    UnknownSourceError,
    get_source,
    preferred_source,
)
from arcturus_api.infrastructure.providers.directories.adapters import DIRECTORY_PROVIDERS
from arcturus_api.infrastructure.providers.registry import available_providers


class TestRegistryContents:
    def test_source_ids_are_unique(self) -> None:
        ids = [source.source_id for source in SOURCES]
        assert len(ids) == len(set(ids))

    def test_trust_hierarchy_order(self) -> None:
        tier = TRUST_TIER
        assert (
            tier[AuthorityLevel.PRIMARY_REGULATORY]
            == tier[AuthorityLevel.PRIMARY_EXCHANGE]
            == tier[AuthorityLevel.PRIMARY_GOVERNMENT]
            == 1
        )
        assert (
            1
            < tier[AuthorityLevel.PRIMARY_COMPANY]
            < tier[AuthorityLevel.LICENSED_INSTITUTIONAL]
            < tier[AuthorityLevel.SECONDARY]
            < tier[AuthorityLevel.NEWS]
            < tier[AuthorityLevel.ALTERNATIVE]
        )

    def test_social_sources_sit_at_the_bottom(self) -> None:
        lowest = max(TRUST_TIER.values())
        social = [source for source in SOURCES if source.source_type == SourceType.SOCIAL]
        assert social
        assert all(source.trust_tier == lowest for source in social)

    def test_every_live_provider_is_registered_and_enabled(self) -> None:
        for name in available_providers():
            assert get_source(name).enabled
        for provider in DIRECTORY_PROVIDERS.values():
            source = get_source(provider.source_id)
            assert source.enabled
            assert source.implementation_status == ImplementationStatus.IMPLEMENTED

    def test_planned_sources_are_disabled_and_provide_nothing(self) -> None:
        planned = [s for s in SOURCES if s.implementation_status == ImplementationStatus.PLANNED]
        assert planned
        assert all(not source.enabled and source.datasets == () for source in planned)

    def test_licence_claims_carry_a_review_date(self) -> None:
        for source in SOURCES:
            if source.license_status != LicenseStatus.UNKNOWN:
                assert source.terms_checked_on is not None, source.source_id


class TestRegistryInvariants:
    def _variant(self, **changes: object) -> DataSource:
        return DataSource.model_validate({**get_source("nse_archives").model_dump(), **changes})

    def test_planned_source_cannot_be_enabled(self) -> None:
        with pytest.raises(ValidationError, match="not built"):
            self._variant(implementation_status=ImplementationStatus.PLANNED, datasets=())

    def test_tier_must_match_authority(self) -> None:
        with pytest.raises(ValidationError, match="contradicts"):
            self._variant(trust_tier=4)

    def test_licence_claim_without_review_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="review date"):
            self._variant(license_status=LicenseStatus.PERMITTED)

    def test_reviewed_licence_claim_is_accepted(self) -> None:
        source = self._variant(
            license_status=LicenseStatus.PERMITTED, terms_checked_on=date(2026, 9, 15)
        )
        assert source.license_status == LicenseStatus.PERMITTED


class TestPreference:
    def test_more_authoritative_source_is_preferred(self) -> None:
        assert preferred_source("yahoo", "nse_archives") == "nse_archives"
        assert preferred_source("yahoo", "news_web") == "yahoo"

    def test_equal_authority_has_no_preference(self) -> None:
        assert preferred_source("nse_archives", "bse") is None

    def test_unknown_source(self) -> None:
        with pytest.raises(UnknownSourceError):
            get_source("somewhere")
