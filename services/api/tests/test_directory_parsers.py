from arcturus_api.domain.market.models import AssetClass, Exchange
from arcturus_api.infrastructure.providers.directories.parsers import (
    parse_nasdaq_listed,
    parse_nse_equity_csv,
    parse_other_listed,
)

NSE_CSV = (
    "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE,"
    " MARKET LOT, ISIN NUMBER, FACE VALUE\n"
    "RELIANCE,Reliance Industries Limited, EQ, 29-NOV-1995, 10, 1, INE002A01018, 10\n"
    "TCS,Tata Consultancy Services Limited, EQ, 25-AUG-2004, 1, 1, INE467B01029, 1\n"
    "SOMEGDR,Some GDR Thing, GB, 01-JAN-2000, 10, 1, INE000000000, 10\n"
)

NASDAQ_LISTED = (
    "Symbol|Security Name|Market Category|Test Issue|Financial Status"
    "|Round Lot Size|ETF|NextShares\n"
    "AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N\n"
    "QQQ|Invesco QQQ Trust|G|N|N|100|Y|N\n"
    "ZTEST|Test Listing|Q|Y|N|100|N|N\n"
    "File Creation Time: 0808202522:01|||||||\n"
)

OTHER_LISTED = (
    "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF"
    "|Round Lot Size|Test Issue|NASDAQ Symbol\n"
    "GE|GE Aerospace|N|GE|N|100|N|GE\n"
    "SPY|SPDR S&P 500 ETF Trust|P|SPY|Y|100|N|SPY\n"
    "AMX-W|Test Warrant|A|AMX-W|N|100|Y|AMX-W\n"
)


class TestNseParser:
    def test_parses_equity_series_only(self) -> None:
        instruments = parse_nse_equity_csv(NSE_CSV)
        symbols = [str(item.symbol) for item in instruments]
        assert symbols == ["NSE:RELIANCE", "NSE:TCS"]
        assert instruments[0].name == "Reliance Industries Limited"
        assert instruments[0].currency == "INR"
        assert instruments[0].asset_class == AssetClass.EQUITY
        assert [item.isin for item in instruments] == ["INE002A01018", "INE467B01029"]


class TestNasdaqParser:
    def test_parses_and_flags_etfs(self) -> None:
        instruments = parse_nasdaq_listed(NASDAQ_LISTED)
        by_ticker = {item.symbol.ticker: item for item in instruments}
        assert set(by_ticker) == {"AAPL", "QQQ"}  # test issue excluded
        assert by_ticker["AAPL"].asset_class == AssetClass.EQUITY
        assert by_ticker["QQQ"].asset_class == AssetClass.ETF
        assert by_ticker["AAPL"].symbol.exchange == Exchange.NASDAQ


class TestOtherListedParser:
    def test_maps_exchanges_and_skips_unknown(self) -> None:
        instruments = parse_other_listed(OTHER_LISTED)
        assert len(instruments) == 1  # P (Arca) skipped, test issue skipped
        assert str(instruments[0].symbol) == "NYSE:GE"
        assert instruments[0].currency == "USD"
