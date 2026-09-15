"""Data quality use cases (shared data platform)."""

from datetime import UTC, datetime

from arcturus_api.application.market.service import MarketDataService
from arcturus_api.domain.market.models import Interval
from arcturus_api.domain.quality.candles import assess_candles
from arcturus_api.domain.quality.models import DataQualityReport


class DataQualityService:
    def __init__(self, market: MarketDataService) -> None:
        self._market = market

    async def assess_candles(
        self, raw_symbol: str, interval: Interval = Interval.DAY_1
    ) -> DataQualityReport:
        """Validate the default candle window the rest of the platform consumes."""
        candles = await self._market.get_candles(raw_symbol, interval)
        return assess_candles(candles, now=datetime.now(UTC), source_id=self._market.provider_name)
