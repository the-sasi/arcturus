import time
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from arcturus_api.domain.market.errors import ProviderUnavailableError
from arcturus_api.domain.market.models import Quote, Symbol
from arcturus_api.infrastructure.providers.yahoo.adapter import (
    YahooMarketDataProvider,
    to_yahoo_ticker,
)


class HangingYahoo(YahooMarketDataProvider):
    def _get_quote_sync(self, symbol: Symbol) -> Quote:
        time.sleep(0.3)  # simulates a Yahoo call that never answers in time
        return Quote(symbol=symbol, price=Decimal("1"), as_of=datetime.now(UTC))


class TestYahooTimeouts:
    async def test_hung_call_becomes_provider_unavailable(self) -> None:
        provider = HangingYahoo(timeout_seconds=0.05)
        with pytest.raises(ProviderUnavailableError, match="timed out"):
            await provider.get_quote(Symbol.parse("NSE:TCS"))


class TestYahooTickerMapping:
    def test_nse_gets_ns_suffix(self) -> None:
        assert to_yahoo_ticker(Symbol.parse("NSE:RELIANCE")) == "RELIANCE.NS"

    def test_bse_gets_bo_suffix(self) -> None:
        assert to_yahoo_ticker(Symbol.parse("BSE:TCS")) == "TCS.BO"

    def test_us_exchanges_are_bare(self) -> None:
        assert to_yahoo_ticker(Symbol.parse("NASDAQ:AAPL")) == "AAPL"
        assert to_yahoo_ticker(Symbol.parse("NYSE:GE")) == "GE"

    def test_index_tickers_pass_through(self) -> None:
        assert to_yahoo_ticker(Symbol.parse("INDEX:^NSEI")) == "^NSEI"
        assert to_yahoo_ticker(Symbol.parse("INDEX:^GSPC")) == "^GSPC"
