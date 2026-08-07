from arcturus_api.domain.market.models import Exchange, Symbol


class TestSymbolParse:
    def test_namespaced_symbol(self) -> None:
        symbol = Symbol.parse("NSE:RELIANCE")
        assert symbol.exchange == Exchange.NSE
        assert symbol.ticker == "RELIANCE"

    def test_bare_ticker_defaults_to_nasdaq(self) -> None:
        symbol = Symbol.parse("AAPL")
        assert symbol.exchange == Exchange.NASDAQ
        assert symbol.ticker == "AAPL"

    def test_lowercase_is_normalised(self) -> None:
        symbol = Symbol.parse("nse:reliance")
        assert symbol.exchange == Exchange.NSE
        assert symbol.ticker == "RELIANCE"

    def test_unknown_exchange_maps_to_other(self) -> None:
        symbol = Symbol.parse("LSE:VOD")
        assert symbol.exchange == Exchange.OTHER
        assert symbol.ticker == "VOD"

    def test_round_trip_string(self) -> None:
        assert str(Symbol.parse("BSE:TCS")) == "BSE:TCS"
