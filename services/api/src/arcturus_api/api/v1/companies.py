"""Company endpoints (shared data platform): identity today, company data later."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from arcturus_api.api.deps import get_identity_service
from arcturus_api.application.identity.service import EntityResolutionService
from arcturus_api.domain.identity.models import (
    CompanyIdentity,
    EntityNotFoundError,
    InvalidIdentifierError,
)

router = APIRouter(prefix="/companies", tags=["companies"])

Identity = Annotated[EntityResolutionService, Depends(get_identity_service)]


@router.get("/{identifier}/identity")
async def get_company_identity(
    identifier: str,
    service: Identity,
    as_of: Annotated[datetime | None, Query()] = None,
) -> CompanyIdentity:
    """Resolve ``NSE:SYMBOL``, ``BSE:SCRIPCODE`` or an ISIN to one company.

    Returns every identifier Arcturus has observed with its provenance.
    ``as_of`` resolves point-in-time: only identifiers observed by then count.
    """
    try:
        return await service.resolve(identifier, as_of)
    except InvalidIdentifierError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
