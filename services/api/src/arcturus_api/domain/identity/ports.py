"""Hexagonal port for company identity and data-conflict persistence."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from arcturus_api.domain.data.conflicts import DataConflict, ResolutionStatus
from arcturus_api.domain.identity.models import (
    CompanyIdentity,
    IdentifierKey,
    IdentifierScheme,
    IdentitySyncPlan,
    IdentitySyncResult,
)
from arcturus_api.domain.quality.models import DataQualityReport


class CompanyIdentityRepository(ABC):
    @abstractmethod
    async def find(
        self, key: IdentifierKey, as_of: datetime | None = None
    ) -> CompanyIdentity | None:
        """The company holding this identifier.

        Without ``as_of``: active identifiers only. With ``as_of``: identifiers
        Arcturus had observed by then and not yet seen superseded (point-in-time).
        """

    @abstractmethod
    async def active_identifiers(self, schemes: set[IdentifierScheme]) -> dict[IdentifierKey, UUID]:
        """Every active identifier of the given schemes, mapped to its company."""

    @abstractmethod
    async def apply_sync(
        self,
        plan: IdentitySyncPlan,
        source_id: str,
        observed_at: datetime,
        quality: DataQualityReport,
    ) -> IdentitySyncResult:
        """Apply a plan atomically; re-detected open conflicts are not duplicated."""

    @abstractmethod
    async def list_conflicts(
        self, status: ResolutionStatus | None, limit: int, offset: int
    ) -> tuple[list[DataConflict], int]:
        """Most recently detected first."""
