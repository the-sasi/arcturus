from datetime import UTC, datetime
from decimal import Decimal

from arcturus_api.application.market.service import MOVERS_UNIVERSE, MarketDataService
from arcturus_api.domain.market.errors import SymbolNotFoundError
from arcturus_api.domain.market.models import CandleSeries, Interval, Quote, Symbol
from arcturus_api.domain.market.ports import MarketDataProvider


class ScriptedProvider(MarketDataProvider):
    """Returns a deterministic change% per ticker; fails for tickers in `broken`."""

    name = "scripted"

    def __init__(self, changes: dict[str, str], broken: set[str] | None = None) -> None:
        self._changes = changes
        self._broken = broken or set()

    async def get_quote(self, symbol: Symbol) -> Quote:
        if symbol.ticker in self._broken:
            raise SymbolNotFoundError(str(symbol))
        change = Decimal(self._changes.get(symbol.ticker, "0"))
        return Quote(
            symbol=symbol,
            price=Decimal("100") + change,
            previous_close=Decimal("100"),
            change=change,
            change_percent=change,
            as_of=datetime.now(UTC),
        )

    async def get_candles(
        self, symbol: Symbol, interval: Interval, start: datetime, end: datetime
    ) -> CandleSeries:
        raise NotImplementedError


class TestMovers:
    async def test_ranks_gainers_and_losers(self) -> None:
        provider = ScriptedProvider({"RELIANCE": "5.0", "TCS": "-4.0", "INFY": "2.0"})
        service = MarketDataService(provider)

        snapshot = await service.get_movers()

        assert snapshot.universe_size == len(MOVERS_UNIVERSE)
        assert str(snapshot.gainers[0].symbol) == "NSE:RELIANCE"
        assert str(snapshot.losers[0].symbol) == "NSE:TCS"
        assert snapshot.advancing == 2
        assert snapshot.declining == 1
        # flat (0%) symbols are excluded from both lists
        gainer_tickers = {quote.symbol.ticker for quote in snapshot.gainers}
        loser_tickers = {quote.symbol.ticker for quote in snapshot.losers}
        assert "HDFCBANK" not in gainer_tickers | loser_tickers

    async def test_individual_failures_are_skipped(self) -> None:
        provider = ScriptedProvider({"TCS": "1.0"}, broken={"RELIANCE"})
        service = MarketDataService(provider)

        snapshot = await service.get_movers()

        assert snapshot.quoted == len(MOVERS_UNIVERSE) - 1
        assert all(quote.symbol.ticker != "RELIANCE" for quote in snapshot.gainers)
