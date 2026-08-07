"""Watchlist CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from arcturus_api.api.deps import get_watchlist_service
from arcturus_api.application.watchlist.service import WatchlistService
from arcturus_api.domain.watchlist.errors import (
    DuplicateWatchlistItemError,
    DuplicateWatchlistNameError,
    WatchlistItemNotFoundError,
    WatchlistNotFoundError,
)
from arcturus_api.domain.watchlist.models import Watchlist

router = APIRouter(prefix="/watchlists", tags=["watchlists"])

Service = Annotated[WatchlistService, Depends(get_watchlist_service)]


class CreateWatchlistRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class AddItemRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40, examples=["NSE:RELIANCE"])


@router.get("")
async def list_watchlists(service: Service) -> list[Watchlist]:
    return await service.list_watchlists()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_watchlist(body: CreateWatchlistRequest, service: Service) -> Watchlist:
    try:
        return await service.create_watchlist(body.name)
    except DuplicateWatchlistNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{watchlist_id}")
async def get_watchlist(watchlist_id: UUID, service: Service) -> Watchlist:
    try:
        return await service.get_watchlist(watchlist_id)
    except WatchlistNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(watchlist_id: UUID, service: Service) -> None:
    try:
        await service.delete_watchlist(watchlist_id)
    except WatchlistNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{watchlist_id}/items", status_code=status.HTTP_201_CREATED)
async def add_item(watchlist_id: UUID, body: AddItemRequest, service: Service) -> Watchlist:
    try:
        return await service.add_symbol(watchlist_id, body.symbol)
    except WatchlistNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DuplicateWatchlistItemError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{watchlist_id}/items/{symbol}")
async def remove_item(watchlist_id: UUID, symbol: str, service: Service) -> Watchlist:
    try:
        return await service.remove_symbol(watchlist_id, symbol)
    except (WatchlistNotFoundError, WatchlistItemNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
