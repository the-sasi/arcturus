"""Strategy evaluation use cases.

Verdicts are gated by the market regime: the same setup deserves less trust
in a downtrending market. Adjustments are deterministic and always explained
in the verdict's reasons.
"""

import logging

from arcturus_api.application.market.regime_service import RegimeService
from arcturus_api.application.market.service import MarketDataService
from arcturus_api.domain.market.models import Interval, Symbol
from arcturus_api.domain.market.regime import MarketRegime, RegimeState
from arcturus_api.domain.strategy.models import (
    InsufficientHistoryError,
    Stance,
    StrategyMetadata,
    StrategyVerdict,
)
from arcturus_api.domain.strategy.plugins import ALL_STRATEGIES

logger = logging.getLogger(__name__)

# Confidence adjustment for BULLISH verdicts by (regime, strategy style)
_BULLISH_ADJUSTMENT: dict[RegimeState, dict[str, int]] = {
    RegimeState.RISK_ON: {"trend-following": 5, "breakout": 5, "mean-reversion": 0},
    RegimeState.MIXED: {"trend-following": -5, "breakout": -5, "mean-reversion": 0},
    RegimeState.RISK_OFF: {"trend-following": -15, "breakout": -15, "mean-reversion": -10},
}


def apply_regime_gate(verdict: StrategyVerdict, regime: MarketRegime) -> StrategyVerdict:
    if verdict.stance != Stance.BULLISH:
        return verdict
    adjustment = _BULLISH_ADJUSTMENT[regime.state].get(verdict.strategy.style, 0)
    if adjustment == 0:
        return verdict
    direction = "boosted" if adjustment > 0 else "reduced"
    reason = (
        f"Market regime is {regime.state.value.replace('_', '-')}: {regime.description} "
        f"Confidence {direction} by {abs(adjustment)}."
    )
    return verdict.model_copy(
        update={
            "confidence": max(0, min(100, verdict.confidence + adjustment)),
            "reasons": [*verdict.reasons, reason],
        }
    )


class StrategyService:
    def __init__(self, market: MarketDataService, regime: RegimeService | None = None) -> None:
        self._market = market
        self._regime = regime

    def list_strategies(self) -> list[StrategyMetadata]:
        return [strategy.metadata for strategy in ALL_STRATEGIES]

    async def evaluate_all(self, raw_symbol: str) -> list[StrategyVerdict]:
        """Run every registered strategy on daily candles; skip those lacking history."""
        candles = await self._market.get_candles(raw_symbol, Interval.DAY_1)

        regime: MarketRegime | None = None
        if self._regime is not None:
            try:
                regime = await self._regime.get_regime(Symbol.parse(raw_symbol).exchange)
            except Exception:
                logger.warning("regime unavailable; verdicts ungated", exc_info=True)

        verdicts: list[StrategyVerdict] = []
        for strategy in ALL_STRATEGIES:
            try:
                verdict = strategy.evaluate(candles)
            except InsufficientHistoryError as exc:
                logger.info("skipping %s for %s: %s", strategy.metadata.key, raw_symbol, exc)
                continue
            verdicts.append(apply_regime_gate(verdict, regime) if regime else verdict)
        return verdicts
