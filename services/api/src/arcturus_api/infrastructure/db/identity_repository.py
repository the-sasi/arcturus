"""SQLAlchemy implementation of the CompanyIdentityRepository port."""

import logging
import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from arcturus_api.domain.data.conflicts import (
    ConflictClassification,
    ConflictType,
    DataConflict,
    NewConflict,
    ResolutionStatus,
)
from arcturus_api.domain.data.provenance import provenance_for
from arcturus_api.domain.identity.models import (
    LISTING_SCHEMES,
    CompanyIdentifier,
    CompanyIdentity,
    IdentifierKey,
    IdentifierScheme,
    IdentitySyncPlan,
    IdentitySyncResult,
)
from arcturus_api.domain.identity.ports import CompanyIdentityRepository
from arcturus_api.domain.quality.models import DataQualityReport
from arcturus_api.infrastructure.db.orm import CompanyIdentifierRow, CompanyRow, DataConflictRow

logger = logging.getLogger(__name__)

_CHUNK = 500
_EXCHANGE_BY_SCHEME = {scheme: exchange for exchange, scheme in LISTING_SCHEMES.items()}

_ConflictKey = tuple[str, str, str, str, str | None, str, str | None]


def _valid_at(as_of: datetime | None) -> ColumnElement[bool]:
    """Active now, or — point in time — observed by ``as_of`` and not yet superseded."""
    if as_of is None:
        return CompanyIdentifierRow.active.is_(True)
    return and_(
        CompanyIdentifierRow.first_seen_at <= as_of,
        or_(CompanyIdentifierRow.active.is_(True), CompanyIdentifierRow.last_seen_at >= as_of),
    )


def _conflict_key(conflict: NewConflict) -> _ConflictKey:
    return (
        conflict.conflict_type.value,
        conflict.subject,
        conflict.metric,
        conflict.source_a_id,
        conflict.value_a,
        conflict.source_b_id,
        conflict.value_b,
    )


def _row_conflict_key(row: DataConflictRow) -> _ConflictKey:
    return (
        row.conflict_type,
        row.subject,
        row.metric,
        row.source_a_id,
        row.value_a,
        row.source_b_id,
        row.value_b,
    )


def _conflict_to_domain(row: DataConflictRow) -> DataConflict:
    return DataConflict(
        id=row.id,
        conflict_type=ConflictType(row.conflict_type),
        entity_id=row.entity_id,
        subject=row.subject,
        metric=row.metric,
        source_a_id=row.source_a_id,
        value_a=row.value_a,
        source_b_id=row.source_b_id,
        value_b=row.value_b,
        classification=ConflictClassification(row.classification),
        preferred_source_id=row.preferred_source_id,
        reason=row.reason,
        resolution_status=ResolutionStatus(row.resolution_status),
        detected_at=row.detected_at,
        last_detected_at=row.last_detected_at,
    )


class SqlAlchemyCompanyIdentityRepository(CompanyIdentityRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def find(
        self, key: IdentifierKey, as_of: datetime | None = None
    ) -> CompanyIdentity | None:
        async with self._session_factory() as session:
            company_ids = set(
                (
                    await session.scalars(
                        select(CompanyIdentifierRow.company_id).where(
                            CompanyIdentifierRow.scheme == key.scheme.value,
                            CompanyIdentifierRow.value == key.value,
                            _valid_at(as_of),
                        )
                    )
                ).all()
            )
            if not company_ids:
                return None
            if len(company_ids) > 1:
                # Never pick one silently; the linker prevents this for active identifiers
                logger.warning(
                    "identifier %s held by %d companies at %s", key, len(company_ids), as_of
                )
                return None
            return await self._identity(session, company_ids.pop(), as_of)

    async def _identity(
        self, session: AsyncSession, company_id: UUID, as_of: datetime | None
    ) -> CompanyIdentity:
        company = await session.get(CompanyRow, company_id)
        if company is None:
            raise LookupError(f"company {company_id} vanished mid-read")

        history = select(CompanyIdentifierRow).where(CompanyIdentifierRow.company_id == company_id)
        if as_of is not None:
            history = history.where(CompanyIdentifierRow.first_seen_at <= as_of)
        rows = (
            await session.scalars(
                history.order_by(CompanyIdentifierRow.scheme, CompanyIdentifierRow.first_seen_at)
            )
        ).all()
        listing_rows = (
            await session.scalars(
                select(CompanyIdentifierRow).where(
                    CompanyIdentifierRow.company_id == company_id,
                    CompanyIdentifierRow.scheme.in_([s.value for s in _EXCHANGE_BY_SCHEME]),
                    _valid_at(as_of),
                )
            )
        ).all()
        open_conflicts = await session.scalar(
            select(func.count())
            .select_from(DataConflictRow)
            .where(
                DataConflictRow.entity_id == company_id,
                DataConflictRow.resolution_status == ResolutionStatus.OPEN.value,
            )
        )
        return CompanyIdentity(
            company_id=company.id,
            name=company.name,
            country=company.country,
            identifiers=[
                CompanyIdentifier(
                    scheme=IdentifierScheme(row.scheme),
                    value=row.value,
                    active=row.active,
                    first_seen_at=row.first_seen_at,
                    last_seen_at=row.last_seen_at,
                    provenance=provenance_for(
                        row.source_id, row.last_seen_at, entity_id=str(company.id)
                    ),
                )
                for row in rows
            ],
            canonical_symbols=sorted(
                f"{_EXCHANGE_BY_SCHEME[IdentifierScheme(row.scheme)].value}:{row.value}"
                for row in listing_rows
            ),
            open_conflicts=int(open_conflicts or 0),
        )

    async def active_identifiers(self, schemes: set[IdentifierScheme]) -> dict[IdentifierKey, UUID]:
        async with self._session_factory() as session:
            rows = await session.execute(
                select(
                    CompanyIdentifierRow.scheme,
                    CompanyIdentifierRow.value,
                    CompanyIdentifierRow.company_id,
                ).where(
                    CompanyIdentifierRow.active.is_(True),
                    CompanyIdentifierRow.scheme.in_([scheme.value for scheme in schemes]),
                )
            )
            return {
                IdentifierKey(scheme=IdentifierScheme(scheme), value=value): company_id
                for scheme, value, company_id in rows
            }

    async def apply_sync(
        self,
        plan: IdentitySyncPlan,
        source_id: str,
        observed_at: datetime,
        quality: DataQualityReport,
    ) -> IdentitySyncResult:
        added = 0
        deactivated = 0
        async with self._session_factory() as session:
            touched_schemes = {
                key.scheme.value
                for update in plan.updates
                for key in (*update.touch, *update.add, *update.deactivate)
            }
            index: dict[tuple[UUID, str, str], CompanyIdentifierRow] = {}
            if touched_schemes:
                existing = await session.scalars(
                    select(CompanyIdentifierRow).where(
                        CompanyIdentifierRow.scheme.in_(sorted(touched_schemes))
                    )
                )
                index = {(row.company_id, row.scheme, row.value): row for row in existing}

            companies: dict[UUID, CompanyRow] = {}
            update_ids = [update.company_id for update in plan.updates]
            for start in range(0, len(update_ids), _CHUNK):
                chunk = update_ids[start : start + _CHUNK]
                for company in await session.scalars(
                    select(CompanyRow).where(CompanyRow.id.in_(chunk))
                ):
                    companies[company.id] = company

            for new in plan.creates:
                company = CompanyRow(id=uuid.uuid4(), name=new.name, country=new.country)
                session.add(company)
                for key in new.identifiers:
                    session.add(self._identifier_row(company.id, key, source_id, observed_at))
                    added += 1

            for update in plan.updates:
                company_row = companies.get(update.company_id)
                if company_row is None:
                    raise LookupError(f"company {update.company_id} not found while applying sync")
                if company_row.name != update.name:
                    company_row.name = update.name
                for key in update.touch:
                    row = index.get((update.company_id, key.scheme.value, key.value))
                    if row is not None:
                        row.last_seen_at = observed_at
                for key in update.deactivate:
                    row = index.get((update.company_id, key.scheme.value, key.value))
                    if row is not None and row.active:
                        row.active = False
                        deactivated += 1
                for key in update.add:
                    row = index.get((update.company_id, key.scheme.value, key.value))
                    if row is None:
                        session.add(
                            self._identifier_row(update.company_id, key, source_id, observed_at)
                        )
                        added += 1
                    elif not row.active:
                        row.active = True
                        row.last_seen_at = observed_at
                        added += 1
                    else:
                        row.last_seen_at = observed_at

            opened, redetected = await self._record_conflicts(session, plan.conflicts, observed_at)
            await session.commit()

        return IdentitySyncResult(
            source_id=source_id,
            applied=True,
            quality=quality,
            companies_created=len(plan.creates),
            companies_updated=len(plan.updates),
            identifiers_added=added,
            identifiers_deactivated=deactivated,
            conflicts_opened=opened,
            conflicts_redetected=redetected,
        )

    @staticmethod
    def _identifier_row(
        company_id: UUID, key: IdentifierKey, source_id: str, observed_at: datetime
    ) -> CompanyIdentifierRow:
        return CompanyIdentifierRow(
            company_id=company_id,
            scheme=key.scheme.value,
            value=key.value,
            active=True,
            source_id=source_id,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
        )

    @staticmethod
    async def _record_conflicts(
        session: AsyncSession, conflicts: list[NewConflict], observed_at: datetime
    ) -> tuple[int, int]:
        if not conflicts:
            return 0, 0
        open_rows = await session.scalars(
            select(DataConflictRow).where(
                DataConflictRow.resolution_status == ResolutionStatus.OPEN.value
            )
        )
        known = {_row_conflict_key(row): row for row in open_rows}
        opened = 0
        redetected = 0
        for conflict in conflicts:
            key = _conflict_key(conflict)
            existing = known.get(key)
            if existing is not None:
                existing.last_detected_at = observed_at
                redetected += 1
                continue
            row = DataConflictRow(
                conflict_type=conflict.conflict_type.value,
                entity_id=conflict.entity_id,
                subject=conflict.subject,
                metric=conflict.metric,
                source_a_id=conflict.source_a_id,
                value_a=conflict.value_a,
                source_b_id=conflict.source_b_id,
                value_b=conflict.value_b,
                classification=conflict.classification.value,
                resolution_status=ResolutionStatus.OPEN.value,
                preferred_source_id=conflict.preferred_source_id,
                reason=conflict.reason,
                detected_at=observed_at,
                last_detected_at=observed_at,
            )
            session.add(row)
            known[key] = row
            opened += 1
        return opened, redetected

    async def list_conflicts(
        self, status: ResolutionStatus | None, limit: int, offset: int
    ) -> tuple[list[DataConflict], int]:
        stmt = select(DataConflictRow)
        if status is not None:
            stmt = stmt.where(DataConflictRow.resolution_status == status.value)
        async with self._session_factory() as session:
            total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
            rows = await session.scalars(
                stmt.order_by(DataConflictRow.last_detected_at.desc()).limit(limit).offset(offset)
            )
            return [_conflict_to_domain(row) for row in rows], int(total or 0)
