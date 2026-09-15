"""Directory provider adapters: download official listing files."""

import logging

import httpx

from arcturus_api.domain.market.errors import ProviderUnavailableError
from arcturus_api.domain.market.models import Instrument
from arcturus_api.domain.market.ports import InstrumentDirectoryProvider
from arcturus_api.infrastructure.providers.directories.parsers import (
    parse_nasdaq_listed,
    parse_nse_equity_csv,
    parse_other_listed,
)

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

_NSE_EQUITY_URLS = (
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
)
_NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
_OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url)
    response.raise_for_status()
    return response.text


class NseDirectoryProvider(InstrumentDirectoryProvider):
    name = "nse"
    source_id = "nse_archives"

    async def fetch_listings(self) -> list[Instrument]:
        last_error: Exception | None = None
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, headers={"User-Agent": _UA}, follow_redirects=True
        ) as client:
            for url in _NSE_EQUITY_URLS:
                try:
                    text = await _fetch_text(client, url)
                    return parse_nse_equity_csv(text)
                except httpx.HTTPError as exc:
                    logger.warning("NSE listing fetch failed from %s: %s", url, exc)
                    last_error = exc
        raise ProviderUnavailableError(self.name, str(last_error))


class NasdaqTraderDirectoryProvider(InstrumentDirectoryProvider):
    """NASDAQ + NYSE + AMEX from the public Nasdaq Trader symbol directory."""

    name = "nasdaqtrader"
    source_id = "nasdaqtrader"

    async def fetch_listings(self) -> list[Instrument]:
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT, headers={"User-Agent": _UA}, follow_redirects=True
            ) as client:
                nasdaq_text = await _fetch_text(client, _NASDAQ_LISTED_URL)
                other_text = await _fetch_text(client, _OTHER_LISTED_URL)
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(self.name, str(exc)) from exc
        return parse_nasdaq_listed(nasdaq_text) + parse_other_listed(other_text)


DIRECTORY_PROVIDERS: dict[str, type[InstrumentDirectoryProvider]] = {
    "nse": NseDirectoryProvider,
    "nasdaqtrader": NasdaqTraderDirectoryProvider,
}
