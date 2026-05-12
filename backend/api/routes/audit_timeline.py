"""Audit timeline API routes — append-only, cross-entity feed, paginated."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.enums import AuditActorType
from services.audit_timeline import AuditTimelineRuntime

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actor_id: UUID | None
    actor_type: AuditActorType
    action: str
    target_type: str
    target_id: UUID | None
    correlation_id: UUID | None
    ip_address: str | None
    user_agent: str | None
    payload: dict
    created_at: object


class AuditAppendBody(BaseModel):
    action: str
    target_type: str
    actor_type: AuditActorType = AuditActorType.system
    actor_id: UUID | None = None
    target_id: UUID | None = None
    correlation_id: UUID | None = None
    payload: dict = {}
    ip_address: str | None = None
    user_agent: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
async def append_audit_event(
    body: AuditAppendBody,
    session: AsyncSession = Depends(get_session),
) -> AuditLogResponse:
    rt = AuditTimelineRuntime(session)
    entry = await rt.append(
        action=body.action,
        target_type=body.target_type,
        actor_type=body.actor_type,
        actor_id=body.actor_id,
        target_id=body.target_id,
        correlation_id=body.correlation_id,
        payload=body.payload,
        ip_address=body.ip_address,
        user_agent=body.user_agent,
    )
    return AuditLogResponse.model_validate(entry)


@router.get("", response_model=dict)
async def get_timeline(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    actor_id: UUID | None = Query(None),
    target_type: str | None = Query(None),
    target_id: UUID | None = Query(None),
    action: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = AuditTimelineRuntime(session)
    result = await rt.get_timeline(
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        action=action,
    )
    return {
        "items": [AuditLogResponse.model_validate(e).model_dump() for e in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/correlation/{correlation_id}", response_model=dict)
async def get_by_correlation(
    correlation_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = AuditTimelineRuntime(session)
    result = await rt.get_by_correlation(correlation_id, page=page, page_size=page_size)
    return {
        "items": [AuditLogResponse.model_validate(e).model_dump() for e in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }
