"""Market regime: is the overall market healthy, shaky, or in a downtrend?

Deterministic read of a benchmark index:
- RISK_ON:  index above its 200-day average AND 50-day average rising
- RISK_OFF: index below its 200-day average
- MIXED:    everything else
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from arcturus_api.domain.indicators.library import sma
from arcturus_api.domain.market.models import Symbol


class RegimeState(StrEnum):
    RISK_ON = "risk_on"
    MIXED = "mixed"
    RISK_OFF = "risk_off"


class MarketRegime(BaseModel):
    model_config = ConfigDict(frozen=True)

    index_symbol: Symbol
    state: RegimeState
    index_close: float
    sma_50: float | None
    sma_200: float | None
    description: str
    as_of: datetime


def compute_regime(index_symbol: Symbol, closes: list[float], as_of: datetime) -> MarketRegime:
    close = closes[-1]
    sma50_series = sma(closes, 50) if len(closes) >= 50 else [None]
    sma200_series = sma(closes, 200) if len(closes) >= 200 else [None]
    sma50 = sma50_series[-1]
    sma200 = sma200_series[-1]

    if sma200 is None:
        # Not enough history to judge — treat as mixed, never as confidently safe
        return MarketRegime(
            index_symbol=index_symbol,
            state=RegimeState.MIXED,
            index_close=round(close, 2),
            sma_50=round(sma50, 2) if sma50 is not None else None,
            sma_200=None,
            description="Insufficient index history to judge the regime.",
            as_of=as_of,
        )

    sma50_rising = (
        sma50 is not None
        and len(sma50_series) >= 11
        and sma50_series[-11] is not None
        and sma50 > sma50_series[-11]
    )

    if close < sma200:
        state = RegimeState.RISK_OFF
        description = (
            f"Index {close:.0f} is below its 200-day average ({sma200:.0f}) — "
            "downtrending market; bullish signals are less reliable."
        )
    elif sma50_rising:
        state = RegimeState.RISK_ON
        description = (
            f"Index {close:.0f} is above its 200-day average ({sma200:.0f}) "
            "with a rising 50-day average — healthy market."
        )
    else:
        state = RegimeState.MIXED
        description = (
            f"Index {close:.0f} is above its 200-day average ({sma200:.0f}) "
            "but the 50-day average is flat/falling — indecisive market."
        )

    return MarketRegime(
        index_symbol=index_symbol,
        state=state,
        index_close=round(close, 2),
        sma_50=round(sma50, 2) if sma50 is not None else None,
        sma_200=round(sma200, 2),
        description=description,
        as_of=as_of,
    )
