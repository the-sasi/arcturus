"""API v1 aggregate router."""

from fastapi import APIRouter

from arcturus_api.api.v1 import market

router = APIRouter()
router.include_router(market.router)
