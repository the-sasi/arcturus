"""Entity resolution use cases (shared data platform).

Domain-agnostic: both the future Trading and Investing modules resolve
companies through here; nothing in this service interprets the data.
"""

import logging
from datetime import UTC, datetime

from arcturus_api.domain.data.conflicts import DataConflictPage, ResolutionStatus
from arcturus_api.domain.data.sources import get_source
from arcturus_api.domain.identity.identifiers import parse_identifier
from arcturus_api.domain.identity.linking import plan_listing_sync
from arcturus_api.domain.identity.models import (
    LISTING_SCHEMES,
    CompanyIdentity,
    EntityNotFoundError,
    IdentifierScheme,
    IdentitySyncResult,
)
from arcturus_api.domain.identity.ports import CompanyIdentityRepository
from arcturus_api.domain.market.models import Instrument
from arcturus_api.domain.quality.listings import assess_listings
from arcturus_api.domain.quality.models import QualityStatus

logger = logging.getLogger(__name__)


class EntityResolutionService:
    def __init__(self, repository: CompanyIdentityRepository) -> None:
        self._repository = repository

    async def resolve(self, raw_identifier: str, as_of: datetime | None = None) -> CompanyIdentity:
        """Resolve NSE:SYMBOL, BSE:SCRIPCODE or an ISIN to one company.

        Raises InvalidIdentifierError for unparseable input and
        EntityNotFoundError when no company holds the identifier.
        """
        key = parse_identifier(raw_identifier)
        identity = await self._repository.find(key, as_of)
        if identity is None:
            raise EntityNotFoundError(raw_identifier)
        return identity

    async def ingest_listings(
        self,
        source_id: str,
        listings: list[Instrument],
        observed_at: datetime | None = None,
    ) -> IdentitySyncResult:
        """Use listing rows as identity evidence. Idempotent: re-running a batch
        refreshes observations and never duplicates identifiers or conflicts."""
        get_source(source_id)  # identity evidence must come from a registered source
        observed = observed_at or datetime.now(UTC)
        relevant = [item for item in listings if item.symbol.exchange in LISTING_SCHEMES]

        report, accepted = assess_listings(relevant, source_id, observed)
        if report.status == QualityStatus.INVALID:
            logger.warning(
                "identity sync skipped for %s: listing failed quality checks (%s)",
                source_id,
                report.summary(),
            )
            return IdentitySyncResult(source_id=source_id, applied=False, quality=report)

        schemes = {IdentifierScheme.ISIN, *LISTING_SCHEMES.values()}
        active = await self._repository.active_identifiers(schemes)
        plan = plan_listing_sync(accepted, active, source_id)
        result = await self._repository.apply_sync(plan, source_id, observed, report)
        logger.info(
            "identity sync %s: created=%d updated=%d added=%d deactivated=%d "
            "conflicts_opened=%d conflicts_redetected=%d quality=%s",
            source_id,
            result.companies_created,
            result.companies_updated,
            result.identifiers_added,
            result.identifiers_deactivated,
            result.conflicts_opened,
            result.conflicts_redetected,
            report.status.value,
        )
        return result

    async def list_conflicts(
        self, status: ResolutionStatus | None = None, limit: int = 50, offset: int = 0
    ) -> DataConflictPage:
        items, total = await self._repository.list_conflicts(status, limit, offset)
        return DataConflictPage(items=items, total=total, limit=limit, offset=offset)
