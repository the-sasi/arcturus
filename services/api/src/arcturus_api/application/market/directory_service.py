"""Instrument directory use cases: browse, search, sync from exchanges."""

import logging

from arcturus_api.application.identity.service import EntityResolutionService
from arcturus_api.domain.market.directory import DirectorySyncResult, InstrumentPage, SyncStatus
from arcturus_api.domain.market.models import Exchange
from arcturus_api.domain.market.ports import InstrumentDirectoryProvider, InstrumentRepository

logger = logging.getLogger(__name__)


class InstrumentDirectoryService:
    def __init__(
        self,
        repository: InstrumentRepository,
        providers: list[InstrumentDirectoryProvider],
        identity: EntityResolutionService | None = None,
    ) -> None:
        self._repository = repository
        self._providers = providers
        self._identity = identity

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
        the others from syncing — and a failure is reported, never silent.
        Listings that carry ISINs also feed entity resolution.
        """
        results: list[DirectorySyncResult] = []
        for provider in self._providers:
            try:
                listings = await provider.fetch_listings()
            except Exception as exc:
                logger.exception("directory sync failed for %s", provider.source_id)
                results.append(
                    DirectorySyncResult(
                        source=provider.source_id,
                        status=SyncStatus.FAILED,
                        fetched=0,
                        upserted=0,
                        error=str(exc),
                    )
                )
                continue
            written = await self._repository.upsert_many(listings)
            identity = None
            if self._identity is not None and any(item.isin for item in listings):
                identity = await self._identity.ingest_listings(provider.source_id, listings)
            results.append(
                DirectorySyncResult(
                    source=provider.source_id,
                    status=SyncStatus.OK,
                    fetched=len(listings),
                    upserted=written,
                    identity=identity,
                )
            )
        return results
