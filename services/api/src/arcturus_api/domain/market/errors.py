"""Market domain errors."""


class MarketDataError(Exception):
    """Base error for market data operations."""


class SymbolNotFoundError(MarketDataError):
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"No data found for symbol: {symbol}")


class ProviderUnavailableError(MarketDataError):
    def __init__(self, provider: str, detail: str = "") -> None:
        self.provider = provider
        super().__init__(f"Provider '{provider}' unavailable. {detail}".strip())


class UnknownProviderError(MarketDataError):
    def __init__(self, provider: str, available: list[str]) -> None:
        self.provider = provider
        super().__init__(f"Unknown provider '{provider}'. Available: {', '.join(available)}")
