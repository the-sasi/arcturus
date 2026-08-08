"""SQLAlchemy implementation of the ExperimentRepository port."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from arcturus_api.domain.research.models import Experiment, ExperimentNotFoundError
from arcturus_api.domain.research.ports import ExperimentRepository
from arcturus_api.infrastructure.db.orm import ExperimentRow


def _to_domain(row: ExperimentRow) -> Experiment:
    return Experiment(
        id=row.id,
        strategy_key=row.strategy_key,
        strategy_version=row.strategy_version,
        symbol=row.symbol,
        interval=row.interval,
        start=row.start,
        end=row.end,
        bars=row.bars,
        config=row.config,
        metrics=row.metrics,
        engine_version=row.engine_version,
        validation=row.validation,
        created_at=row.created_at,
    )


class SqlAlchemyExperimentRepository(ExperimentRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(
        self,
        *,
        strategy_key: str,
        strategy_version: str,
        symbol: str,
        interval: str,
        start: Any,
        end: Any,
        bars: int,
        config: dict[str, Any],
        metrics: dict[str, Any],
        engine_version: str,
        validation: str,
    ) -> Experiment:
        async with self._session_factory() as session:
            row = ExperimentRow(
                strategy_key=strategy_key,
                strategy_version=strategy_version,
                symbol=symbol,
                interval=interval,
                start=start,
                end=end,
                bars=bars,
                config=config,
                metrics=metrics,
                engine_version=engine_version,
                validation=validation,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def list(
        self,
        strategy_key: str | None,
        symbol: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Experiment], int]:
        stmt = select(ExperimentRow)
        if strategy_key:
            stmt = stmt.where(ExperimentRow.strategy_key == strategy_key)
        if symbol:
            stmt = stmt.where(ExperimentRow.symbol == symbol.upper())
        async with self._session_factory() as session:
            total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
            rows = await session.scalars(
                stmt.order_by(ExperimentRow.created_at.desc()).limit(limit).offset(offset)
            )
            return [_to_domain(row) for row in rows], int(total or 0)

    async def get(self, experiment_id: UUID) -> Experiment:
        async with self._session_factory() as session:
            row = await session.get(ExperimentRow, experiment_id)
            if row is None:
                raise ExperimentNotFoundError(experiment_id)
            return _to_domain(row)
