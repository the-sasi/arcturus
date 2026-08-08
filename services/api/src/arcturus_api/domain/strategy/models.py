"""Strategy framework domain models.

Blueprint rules encoded here:
- Strategies are deterministic, versioned plugins — never LLM prompts.
- No blind Buy/Sell commands: verdicts are BULLISH/NEUTRAL/BEARISH stances
  with confidence and explicit reasons, feeding the future Decision Engine.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from arcturus_api.domain.market.models import Symbol


class Stance(StrEnum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


class StrategyMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    version: str
    style: str
    description: str
    typical_holding: str


class PriceZone(BaseModel):
    model_config = ConfigDict(frozen=True)

    low: Decimal
    high: Decimal


class StrategyVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: StrategyMetadata
    symbol: Symbol
    stance: Stance
    # 0-100; deterministic heuristic, NOT a probability of profit
    confidence: int = Field(ge=0, le=100)
    entry_zone: PriceZone | None = None
    stop_loss: Decimal | None = None
    # Plain-language, number-backed reasons — the explainability contract
    reasons: list[str]
    as_of: datetime


class InsufficientHistoryError(Exception):
    def __init__(self, strategy_key: str, needed: int, got: int) -> None:
        super().__init__(f"Strategy '{strategy_key}' needs {needed} candles, got {got}")
        self.strategy_key = strategy_key
