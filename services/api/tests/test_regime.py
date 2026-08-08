from datetime import UTC, datetime

from arcturus_api.application.strategy.service import apply_regime_gate
from arcturus_api.domain.market.models import Symbol
from arcturus_api.domain.market.regime import MarketRegime, RegimeState, compute_regime
from arcturus_api.domain.strategy.models import (
    Stance,
    StrategyMetadata,
    StrategyVerdict,
)

NOW = datetime(2026, 8, 9, tzinfo=UTC)
NIFTY = Symbol.parse("INDEX:^NSEI")


def make_regime(state: RegimeState) -> MarketRegime:
    return MarketRegime(
        index_symbol=NIFTY,
        state=state,
        index_close=24000.0,
        sma_50=24100.0,
        sma_200=23000.0,
        description="test regime",
        as_of=NOW,
    )


def make_verdict(stance: Stance, confidence: int, style: str) -> StrategyVerdict:
    return StrategyVerdict(
        strategy=StrategyMetadata(
            key="test",
            name="Test",
            version="1.0.0",
            style=style,
            description="d",
            typical_holding="n/a",
        ),
        symbol=Symbol.parse("NSE:TCS"),
        stance=stance,
        confidence=confidence,
        entry_zone=None,
        stop_loss=None,
        reasons=["base reason"],
        as_of=NOW,
    )


class TestComputeRegime:
    def test_healthy_uptrend_is_risk_on(self) -> None:
        closes = [100 + 50 * (i / 250) for i in range(250)]
        regime = compute_regime(NIFTY, closes, NOW)
        assert regime.state == RegimeState.RISK_ON

    def test_below_200dma_is_risk_off(self) -> None:
        closes = [150 - 60 * (i / 250) for i in range(250)]
        regime = compute_regime(NIFTY, closes, NOW)
        assert regime.state == RegimeState.RISK_OFF
        assert "below" in regime.description

    def test_above_200dma_with_falling_50dma_is_mixed(self) -> None:
        # Long rise keeps price above the 200-day; recent slide turns the 50-day down
        closes = [100 + 80 * (i / 200) for i in range(200)] + [
            180 - 12 * (i / 50) for i in range(50)
        ]
        regime = compute_regime(NIFTY, closes, NOW)
        assert regime.state == RegimeState.MIXED

    def test_short_history_is_mixed(self) -> None:
        regime = compute_regime(NIFTY, [100.0] * 60, NOW)
        assert regime.state == RegimeState.MIXED
        assert regime.sma_200 is None


class TestRegimeGate:
    def test_risk_off_reduces_bullish_trend_confidence(self) -> None:
        verdict = make_verdict(Stance.BULLISH, 70, "trend-following")
        gated = apply_regime_gate(verdict, make_regime(RegimeState.RISK_OFF))
        assert gated.confidence == 55
        assert any("risk-off" in reason for reason in gated.reasons)

    def test_risk_on_boosts_bullish_trend_confidence(self) -> None:
        verdict = make_verdict(Stance.BULLISH, 70, "trend-following")
        gated = apply_regime_gate(verdict, make_regime(RegimeState.RISK_ON))
        assert gated.confidence == 75

    def test_bearish_verdicts_untouched(self) -> None:
        verdict = make_verdict(Stance.BEARISH, 60, "trend-following")
        gated = apply_regime_gate(verdict, make_regime(RegimeState.RISK_OFF))
        assert gated.confidence == 60
        assert gated.reasons == ["base reason"]

    def test_mean_reversion_unaffected_in_mixed(self) -> None:
        verdict = make_verdict(Stance.BULLISH, 60, "mean-reversion")
        gated = apply_regime_gate(verdict, make_regime(RegimeState.MIXED))
        assert gated.confidence == 60


class TestFrozenCopy:
    def test_gate_returns_new_object(self) -> None:
        verdict = make_verdict(Stance.BULLISH, 70, "breakout")
        gated = apply_regime_gate(verdict, make_regime(RegimeState.RISK_OFF))
        assert verdict.confidence == 70  # original untouched (frozen model)
        assert gated is not verdict
        assert gated.stop_loss == verdict.stop_loss == None  # noqa: E711
