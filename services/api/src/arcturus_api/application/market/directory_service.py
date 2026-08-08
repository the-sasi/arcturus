"""Instrument directory use cases: browse, search, sync from exchanges."""

import logging

from arcturus_api.domain.market.directory import DirectorySyncResult, InstrumentPage
from arcturus_api.domain.market.models import Exchange
from arcturus_api.domain.market.ports import InstrumentDirectoryProvider, InstrumentRepository

logger = logging.getLogger(__name__)


class InstrumentDirectoryService:
    def __init__(
        self,
        repository: InstrumentRepository,
        providers: list[InstrumentDirectoryProvider],
    ) -> None:
        self._repository = repository
        self._providers = providers

    async def search(
        self,
        query: str | None = None,
        exchange: Exchange | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> InstrumentPage:
        items, total = await self._repository.search(query, exchange, limit, offset)
        return InstrumentPage(items=items, total=total, limit=limit, offset=offset)

    async def sync_all(self) -> list[DirectorySyncResult]:
        """Refresh the universe from every configured exchange directory.

        Providers fail independently — one exchange being down must not block
        the others from syncing.
        """
        results: list[DirectorySyncResult] = []
        for provider in self._providers:
            try:
                listings = await provider.fetch_listings()
            except Exception:
                logger.exception("directory sync failed for %s", provider.name)
                results.append(DirectorySyncResult(source=provider.name, fetched=0, upserted=0))
                continue
            written = await self._repository.upsert_many(listings)
            results.append(
                DirectorySyncResult(source=provider.name, fetched=len(listings), upserted=written)
            )
        return results
