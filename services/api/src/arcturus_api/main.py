"""Application entry point — FastAPI app factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arcturus_api import __version__
from arcturus_api.api.v1 import health
from arcturus_api.api.v1.router import router as v1_router
from arcturus_api.application.market.directory_service import InstrumentDirectoryService
from arcturus_api.application.watchlist.service import WatchlistService
from arcturus_api.core.config import get_settings
from arcturus_api.core.logging import configure_logging
from arcturus_api.infrastructure.db.engine import build_engine, build_session_factory
from arcturus_api.infrastructure.db.instrument_repository import SqlAlchemyInstrumentRepository
from arcturus_api.infrastructure.db.watchlist_repository import SqlAlchemyWatchlistRepository
from arcturus_api.infrastructure.providers.directories.adapters import (
    NasdaqTraderDirectoryProvider,
    NseDirectoryProvider,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.debug)
    logger.info("%s v%s starting (%s)", settings.app_name, __version__, settings.environment)

    # Engine creation is lazy — no connection is made until first use, so the
    # API stays up (with /health/ready reporting degraded) when the DB is down.
    engine = build_engine(settings.postgres_dsn, echo=False)
    session_factory = build_session_factory(engine)
    app.state.db_engine = engine
    app.state.watchlist_service = WatchlistService(SqlAlchemyWatchlistRepository(session_factory))
    app.state.directory_service = InstrumentDirectoryService(
        repository=SqlAlchemyInstrumentRepository(session_factory),
        providers=[NseDirectoryProvider(), NasdaqTraderDirectoryProvider()],
    )

    yield

    await engine.dispose()
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
