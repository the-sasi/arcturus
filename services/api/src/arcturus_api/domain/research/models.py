"""Research domain: reproducible experiment records (ADR-008).

An Experiment is the permanent, queryable record of one backtest run —
what was tested, on which data window, with which engine and config, and
what came out. It answers: "exactly which run produced this result?"
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Experiment(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    strategy_key: str
    strategy_version: str
    symbol: str  # canonical EXCHANGE:TICKER
    interval: str
    start: datetime
    end: datetime
    bars: int
    config: dict[str, Any]
    metrics: dict[str, Any]
    engine_version: str
    validation: str
    created_at: datetime


class ExperimentPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Experiment]
    total: int
    limit: int
    offset: int


class ExperimentNotFoundError(Exception):
    def __init__(self, experiment_id: UUID) -> None:
        super().__init__(f"Experiment not found: {experiment_id}")
        self.experiment_id = experiment_id
