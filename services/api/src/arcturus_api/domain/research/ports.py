"""Hexagonal port for experiment persistence."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from arcturus_api.domain.quality.models import DataQualityReport
from arcturus_api.domain.research.models import Experiment


class ExperimentRepository(ABC):
    @abstractmethod
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
        data_quality: DataQualityReport | None = None,
    ) -> Experiment: ...

    @abstractmethod
    async def list(
        self,
        strategy_key: str | None,
        symbol: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Experiment], int]:
        """Newest first."""

    @abstractmethod
    async def get(self, experiment_id: UUID) -> Experiment:
        """Raises ExperimentNotFoundError if absent."""
