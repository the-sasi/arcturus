"""Market domain models.

Asset-class agnostic by design (ADR-006): equities today, options/futures/forex/crypto
tomorrow, with no redesign. Vendor symbol formats never appear here — instruments are
identified by a namespaced ``EXCHANGE:SYMBOL`` string; adapters translate.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssetClass(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    OPTION = "option"
    FUTURE = "future"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    INDEX = "index"


class Exchange(StrEnum):
    NSE = "NSE"
    BSE = "BSE"
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"
    AMEX = "AMEX"
    # Market indices (NIFTY, SENSEX, S&P 500, …) — vendor tickers pass through
    INDEX = "INDEX"
    OTHER = "OTHER"


class Interval(StrEnum):
    """Candle intervals. Architecture supports all timeframes from day one."""

    MIN_1 = "1m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    HOUR_1 = "1h"
    DAY_1 = "1d"
    WEEK_1 = "1wk"
    MONTH_1 = "1mo"


class Symbol(BaseModel):
    """Canonical instrument identifier: ``EXCHANGE:TICKER`` (e.g. ``NSE:RELIANCE``)."""

    model_config = ConfigDict(frozen=True)

    exchange: Exchange
    ticker: str

    @classmethod
    def parse(cls, value: str) -> "Symbol":
        """Parse ``EXCHANGE:TICKER``; bare tickers default to NASDAQ."""
        if ":" in value:
            exchange_part, ticker = value.split(":", 1)
            try:
                exchange = Exchange(exchange_part.upper())
            except ValueError:
                exchange = Exchange.OTHER
        else:
            exchange, ticker = Exchange.NASDAQ, value
        return cls(exchange=exchange, ticker=ticker.upper())

    def __str__(self) -> str:
        return f"{self.exchange.value}:{self.ticker}"


class Instrument(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: Symbol
    name: str
    asset_class: AssetClass
    currency: str
    # As reported by the listing source; validated by the data quality engine
    # before it is used as an identity key (persisted in company_identifiers)
    isin: str | None = None
    # Class-specific fields (strike, expiry, contract size, underlying, …)
    attributes: dict[str, Any] = Field(default_factory=dict)


class Quote(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: Symbol
    price: Decimal
    previous_close: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    volume: int | None = None
    currency: str | None = None
    as_of: datetime


class Candle(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class CandleSeries(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: Symbol
    interval: Interval
    candles: list[Candle]
