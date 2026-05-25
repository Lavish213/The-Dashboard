"""Operator session API routes — heartbeat, admin force-disconnect, stale cleanup."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.enums import RealtimeSessionStatus
from security.auth import get_current_active_user
from services.operator_sessions import OperatorSessionRuntime

router = APIRouter(dependencies=[Depends(get_current_active_user)])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RealtimeSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    socket_id: str
    session_status: RealtimeSessionStatus
    connected_at: object
    disconnected_at: object | None
    last_heartbeat_at: object | None
    device_info: str | None


class ConnectBody(BaseModel):
    user_id: UUID
    socket_id: str
    device_info: str | None = None


class StaleCleanupResponse(BaseModel):
    expired_count: int
    session_ids: list[UUID]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=RealtimeSessionResponse, status_code=status.HTTP_201_CREATED)
async def connect_session(
    body: ConnectBody,
    session: AsyncSession = Depends(get_session),
) -> RealtimeSessionResponse:
    rt = OperatorSessionRuntime(session)
    rs = await rt.connect(
        user_id=body.user_id,
        socket_id=body.socket_id,
        device_info=body.device_info,
    )
    return RealtimeSessionResponse.model_validate(rs)


@router.post("/{session_id}/disconnect", response_model=RealtimeSessionResponse)
async def disconnect_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> RealtimeSessionResponse:
    rt = OperatorSessionRuntime(session)
    rs = await rt.disconnect(session_id)
    return RealtimeSessionResponse.model_validate(rs)


@router.post("/{session_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
async def heartbeat_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    rt = OperatorSessionRuntime(session)
    await rt.heartbeat(session_id)


@router.post("/user/{user_id}/force-disconnect", response_model=list[UUID])
async def force_disconnect_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[UUID]:
    rt = OperatorSessionRuntime(session)
    return await rt.force_disconnect(user_id)


@router.post("/cleanup/stale", response_model=StaleCleanupResponse)
async def cleanup_stale_sessions(
    threshold_seconds: int = Query(90, ge=10),
    session: AsyncSession = Depends(get_session),
) -> StaleCleanupResponse:
    rt = OperatorSessionRuntime(session)
    result = await rt.cleanup_stale(threshold_seconds=threshold_seconds)
    return StaleCleanupResponse(
        expired_count=result.expired_count,
        session_ids=result.session_ids,
    )


@router.get("", response_model=dict)
async def list_active_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = OperatorSessionRuntime(session)
    result = await rt.get_active_sessions(page=page, page_size=page_size)
    return {
        "items": [RealtimeSessionResponse.model_validate(s).model_dump() for s in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/count", response_model=dict)
async def active_session_count(
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = OperatorSessionRuntime(session)
    count = await rt.active_count()
    return {"count": count}
