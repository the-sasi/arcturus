"""API v1 aggregate router."""

from fastapi import APIRouter

from arcturus_api.api.v1 import instruments, market, research, strategies, watchlists

router = APIRouter()
router.include_router(market.router)
router.include_router(instruments.router)
router.include_router(strategies.router)
router.include_router(research.router)
router.include_router(watchlists.router)
