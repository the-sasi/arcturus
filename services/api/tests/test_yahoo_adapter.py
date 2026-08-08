from arcturus_api.domain.market.models import Symbol
from arcturus_api.infrastructure.providers.yahoo.adapter import to_yahoo_ticker


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
