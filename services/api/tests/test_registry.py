import pytest

from arcturus_api.domain.market.errors import UnknownProviderError
from arcturus_api.infrastructure.providers.registry import (
    available_providers,
    create_market_data_provider,
)


class TestProviderRegistry:
    def test_yahoo_is_registered(self) -> None:
        assert "yahoo" in available_providers()

    def test_creates_provider_case_insensitively(self) -> None:
        provider = create_market_data_provider("Yahoo")
        assert provider.name == "yahoo"

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(UnknownProviderError):
            create_market_data_provider("bloomberg")
