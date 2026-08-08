"""Research endpoints: the experiment registry (ADR-008)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from arcturus_api.domain.research.models import Experiment, ExperimentNotFoundError, ExperimentPage
from arcturus_api.domain.research.ports import ExperimentRepository

router = APIRouter(prefix="/research", tags=["research"])


def get_experiment_repository(request: Request) -> ExperimentRepository:
    repository: ExperimentRepository = request.app.state.experiment_repository
    return repository


Experiments = Annotated[ExperimentRepository, Depends(get_experiment_repository)]


@router.get("/experiments")
async def list_experiments(
    repository: Experiments,
    strategy: Annotated[str | None, Query(max_length=64)] = None,
    symbol: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExperimentPage:
    """Recorded backtest experiments, newest first. Filter by strategy/symbol."""
    items, total = await repository.list(strategy, symbol, limit, offset)
    return ExperimentPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: UUID, repository: Experiments) -> Experiment:
    """One experiment with its full config, metrics, and provenance."""
    try:
        return await repository.get(experiment_id)
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
