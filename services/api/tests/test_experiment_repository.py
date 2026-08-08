"""Integration tests for the experiment registry, against in-memory SQLite."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from arcturus_api.domain.research.models import ExperimentNotFoundError
from arcturus_api.infrastructure.db.engine import build_session_factory
from arcturus_api.infrastructure.db.experiment_repository import SqlAlchemyExperimentRepository
from arcturus_api.infrastructure.db.orm import Base

START = datetime(2023, 8, 9, tzinfo=UTC)
END = datetime(2026, 8, 9, tzinfo=UTC)


@pytest.fixture
async def repository() -> AsyncIterator[SqlAlchemyExperimentRepository]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield SqlAlchemyExperimentRepository(build_session_factory(engine))
    await engine.dispose()


async def record_one(
    repository: SqlAlchemyExperimentRepository,
    strategy_key: str = "ema_crossover",
    symbol: str = "NSE:TCS",
) -> None:
    await repository.record(
        strategy_key=strategy_key,
        strategy_version="1.0.0",
        symbol=symbol,
        interval="1d",
        start=START,
        end=END,
        bars=700,
        config={"cost_per_side_pct": 0.2, "entry_confidence": 55},
        metrics={"total_return_pct": 12.9, "annualized_sharpe": 0.42, "trade_count": 6},
        engine_version="1.1.0",
        validation="in-sample-only",
    )


class TestExperimentRepository:
    async def test_record_and_get(self, repository: SqlAlchemyExperimentRepository) -> None:
        await record_one(repository)
        items, total = await repository.list(None, None, limit=10, offset=0)
        assert total == 1
        fetched = await repository.get(items[0].id)
        assert fetched.strategy_key == "ema_crossover"
        assert fetched.metrics["annualized_sharpe"] == 0.42
        assert fetched.engine_version == "1.1.0"
        assert fetched.validation == "in-sample-only"

    async def test_filters(self, repository: SqlAlchemyExperimentRepository) -> None:
        await record_one(repository, "ema_crossover", "NSE:TCS")
        await record_one(repository, "range_breakout", "NSE:TCS")
        await record_one(repository, "ema_crossover", "NSE:RELIANCE")

        _, by_strategy = await repository.list("ema_crossover", None, limit=10, offset=0)
        assert by_strategy == 2
        _, by_symbol = await repository.list(None, "NSE:TCS", limit=10, offset=0)
        assert by_symbol == 2
        _, both = await repository.list("ema_crossover", "NSE:RELIANCE", limit=10, offset=0)
        assert both == 1

    async def test_missing_raises(self, repository: SqlAlchemyExperimentRepository) -> None:
        with pytest.raises(ExperimentNotFoundError):
            await repository.get(uuid4())

    async def test_history_is_append_only(self, repository: SqlAlchemyExperimentRepository) -> None:
        # Two runs of the same strategy+symbol both persist — never overwritten
        await record_one(repository)
        await record_one(repository)
        _, total = await repository.list("ema_crossover", "NSE:TCS", limit=10, offset=0)
        assert total == 2
