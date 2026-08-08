"""Strategy endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from arcturus_api.api.deps import get_backtest_service, get_strategy_service
from arcturus_api.application.strategy.backtest_service import BacktestService
from arcturus_api.application.strategy.service import StrategyService
from arcturus_api.domain.backtest.models import BacktestResult
from arcturus_api.domain.market.errors import ProviderUnavailableError, SymbolNotFoundError
from arcturus_api.domain.strategy.models import (
    InsufficientHistoryError,
    StrategyMetadata,
    StrategyVerdict,
    UnknownStrategyError,
)

router = APIRouter(prefix="/strategies", tags=["strategies"])

Service = Annotated[StrategyService, Depends(get_strategy_service)]
Backtests = Annotated[BacktestService, Depends(get_backtest_service)]


@router.get("")
async def list_strategies(service: Service) -> list[StrategyMetadata]:
    """All registered strategy plugins with their metadata."""
    return service.list_strategies()


@router.get("/backtest/{symbol}")
async def backtest(symbol: str, strategy: str, service: Backtests) -> BacktestResult:
    """Replay a strategy over ~3 years of daily history with realistic costs.

    Past performance does not guarantee future results — this measures how the
    rules WOULD have behaved, nothing more.
    """
    try:
        return await service.backtest(symbol, strategy)
    except UnknownStrategyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InsufficientHistoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/evaluate/{symbol}")
async def evaluate(symbol: str, service: Service) -> list[StrategyVerdict]:
    """Run every strategy on the symbol's daily history.

    Verdicts are rule-based stances with explanations — decision support,
    not financial advice and not orders.
    """
    try:
        return await service.evaluate_all(symbol)
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
