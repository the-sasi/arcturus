"""SQLAlchemy implementation of the InstrumentRepository port."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from arcturus_api.domain.market.models import AssetClass, Exchange, Instrument, Symbol
from arcturus_api.domain.market.ports import InstrumentRepository
from arcturus_api.infrastructure.db.orm import InstrumentRow


def _to_domain(row: InstrumentRow) -> Instrument:
    return Instrument(
        symbol=Symbol(exchange=Exchange(row.exchange), ticker=row.ticker),
        name=row.name,
        asset_class=AssetClass(row.asset_class),
        currency=row.currency,
    )


class SqlAlchemyInstrumentRepository(InstrumentRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search(
        self,
        query: str | None,
        exchange: Exchange | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Instrument], int]:
        stmt = select(InstrumentRow)
        if exchange is not None:
            stmt = stmt.where(InstrumentRow.exchange == exchange.value)
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    InstrumentRow.name.ilike(pattern),
                    InstrumentRow.ticker.ilike(pattern),
                )
            )
        async with self._session_factory() as session:
            total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
            rows = await session.scalars(
                stmt.order_by(InstrumentRow.symbol).limit(limit).offset(offset)
            )
            return [_to_domain(row) for row in rows], int(total or 0)

    async def upsert_many(self, instruments: list[Instrument]) -> int:
        if not instruments:
            return 0
        async with self._session_factory() as session:
            existing = set(
                (
                    await session.scalars(
                        select(InstrumentRow.symbol).where(
                            InstrumentRow.symbol.in_([str(item.symbol) for item in instruments])
                        )
                    )
                ).all()
            )
            written = 0
            for item in instruments:
                key = str(item.symbol)
                if key in existing:
                    row = await session.get(InstrumentRow, key)
                    if row is not None:
                        row.name = item.name
                        row.asset_class = item.asset_class.value
                        row.currency = item.currency
                        written += 1
                    continue
                session.add(
                    InstrumentRow(
                        symbol=key,
                        exchange=item.symbol.exchange.value,
                        ticker=item.symbol.ticker,
                        name=item.name,
                        asset_class=item.asset_class.value,
                        currency=item.currency,
                    )
                )
                written += 1
            await session.commit()
            return written
