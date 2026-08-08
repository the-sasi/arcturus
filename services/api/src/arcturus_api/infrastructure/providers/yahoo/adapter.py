"""Yahoo Finance adapter for the MarketDataProvider port.

All Yahoo-specific concerns live here: ticker suffix mapping, the synchronous
yfinance SDK (offloaded to a thread per ADR-005), and response-shape quirks.
Nothing above this layer knows Yahoo exists.
"""

import asyncio
import logging
import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import yfinance as yf

from arcturus_api.domain.market.errors import ProviderUnavailableError, SymbolNotFoundError
from arcturus_api.domain.market.fundamentals import CompanyProfile, Fundamentals, NewsArticle
from arcturus_api.domain.market.models import (
    Candle,
    CandleSeries,
    Exchange,
    Interval,
    Quote,
    Symbol,
)
from arcturus_api.domain.market.ports import (
    FundamentalDataProvider,
    MarketDataProvider,
    NewsProvider,
)
from arcturus_api.infrastructure.providers.yahoo.parsers import (
    parse_fundamentals,
    parse_news_item,
    parse_profile,
)

logger = logging.getLogger(__name__)

_SUFFIX_BY_EXCHANGE: dict[Exchange, str] = {
    Exchange.NSE: ".NS",
    Exchange.BSE: ".BO",
}

_YF_INTERVAL: dict[Interval, str] = {
    Interval.MIN_1: "1m",
    Interval.MIN_5: "5m",
    Interval.MIN_15: "15m",
    Interval.MIN_30: "30m",
    Interval.HOUR_1: "1h",
    Interval.DAY_1: "1d",
    Interval.WEEK_1: "1wk",
    Interval.MONTH_1: "1mo",
}


def to_yahoo_ticker(symbol: Symbol) -> str:
    """Map canonical ``EXCHANGE:TICKER`` to Yahoo's vendor format."""
    if symbol.exchange == Exchange.INDEX:
        # Index tickers are Yahoo-native (^NSEI, ^GSPC, …)
        return symbol.ticker
    return f"{symbol.ticker}{_SUFFIX_BY_EXCHANGE.get(symbol.exchange, '')}"


def _decimal(value: Any) -> Decimal:
    """Convert vendor floats to Decimal, discarding float representation noise."""
    return Decimal(str(round(float(value), 4)))


class YahooMarketDataProvider(MarketDataProvider, FundamentalDataProvider, NewsProvider):
    name = "yahoo"

    async def get_quote(self, symbol: Symbol) -> Quote:
        return await asyncio.to_thread(self._get_quote_sync, symbol)

    async def get_candles(
        self, symbol: Symbol, interval: Interval, start: datetime, end: datetime
    ) -> CandleSeries:
        return await asyncio.to_thread(self._get_candles_sync, symbol, interval, start, end)

    async def get_profile(self, symbol: Symbol) -> CompanyProfile:
        info = await asyncio.to_thread(self._get_info_sync, symbol)
        return parse_profile(symbol, info)

    async def get_fundamentals(self, symbol: Symbol) -> Fundamentals:
        info = await asyncio.to_thread(self._get_info_sync, symbol)
        return parse_fundamentals(symbol, info)

    async def get_news(self, symbol: Symbol, limit: int = 10) -> list[NewsArticle]:
        raw_items = await asyncio.to_thread(self._get_news_sync, symbol, limit)
        articles = [parse_news_item(item) for item in raw_items]
        return [article for article in articles if article is not None][:limit]

    def _get_info_sync(self, symbol: Symbol) -> dict[str, Any]:
        ticker = yf.Ticker(to_yahoo_ticker(symbol))
        try:
            info: dict[str, Any] = ticker.info or {}
        except Exception as exc:
            raise ProviderUnavailableError(self.name, str(exc)) from exc
        # Yahoo returns a near-empty stub for unknown tickers
        if not info or info.get("regularMarketPrice") is None and "sector" not in info:
            raise SymbolNotFoundError(str(symbol))
        return info

    def _get_news_sync(self, symbol: Symbol, limit: int) -> list[dict[str, Any]]:
        ticker = yf.Ticker(to_yahoo_ticker(symbol))
        try:
            news = ticker.get_news(count=limit)
        except Exception as exc:
            raise ProviderUnavailableError(self.name, str(exc)) from exc
        return news if isinstance(news, list) else []

    def _get_quote_sync(self, symbol: Symbol) -> Quote:
        ticker = yf.Ticker(to_yahoo_ticker(symbol))
        try:
            info: dict[str, Any] = ticker.fast_info or {}
            price = info.get("last_price") or info.get("lastPrice")
            previous_close = info.get("previous_close") or info.get("previousClose")
        except Exception as exc:  # yfinance raises broad exception types
            raise ProviderUnavailableError(self.name, str(exc)) from exc

        if price is None or (isinstance(price, float) and math.isnan(price)):
            raise SymbolNotFoundError(str(symbol))

        price_d = _decimal(price)
        prev_d = _decimal(previous_close) if previous_close else None
        change = price_d - prev_d if prev_d is not None else None
        change_pct = (
            (change / prev_d * 100).quantize(Decimal("0.01"))
            if change is not None and prev_d
            else None
        )
        volume = info.get("last_volume") or info.get("lastVolume")
        return Quote(
            symbol=symbol,
            price=price_d,
            previous_close=prev_d,
            change=change,
            change_percent=change_pct,
            volume=int(volume) if volume else None,
            currency=info.get("currency"),
            as_of=datetime.now(UTC),
        )

    def _get_candles_sync(
        self, symbol: Symbol, interval: Interval, start: datetime, end: datetime
    ) -> CandleSeries:
        ticker = yf.Ticker(to_yahoo_ticker(symbol))
        try:
            frame = ticker.history(
                start=start, end=end, interval=_YF_INTERVAL[interval], auto_adjust=False
            )
        except Exception as exc:
            raise ProviderUnavailableError(self.name, str(exc)) from exc

        if frame.empty:
            raise SymbolNotFoundError(str(symbol))

        candles = [
            Candle(
                timestamp=index.to_pydatetime(),
                open=_decimal(row["Open"]),
                high=_decimal(row["High"]),
                low=_decimal(row["Low"]),
                close=_decimal(row["Close"]),
                volume=int(row["Volume"]),
            )
            for index, row in frame.iterrows()
            if not math.isnan(row["Close"])
        ]
        return CandleSeries(symbol=symbol, interval=interval, candles=candles)
