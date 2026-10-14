"""Call session API routes — deterministic transitions, pagination mandatory."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from calls.repositories import (
    CallEventRepository,
    CallParticipantRepository,
    CallSessionRepository,
)
from calls.runtime.presence import PresenceRuntime
from calls.runtime.runtime import CallSessionRuntime
from calls.runtime.states import CallSessionTransitionError
from calls.schemas import (
    CallEventResponse,
    CallParticipantJoin,
    CallParticipantResponse,
    CallSessionCreate,
    CallSessionResponse,
    ConnectionStateResponse,
)
from db.session import get_session
from models.call import Call
from models.call_participant import CallParticipant
from models.enums import CallStatus, UserRole
from models.sophia_session import SophiaSession
from security.permissions import require_permission
from security.rbac import Permission

router = APIRouter(dependencies=[Depends(require_permission(Permission.CALLS_READ))])


async def _require_participant_actor(session, session_id, participant_id, user):
    result = await session.execute(select(CallParticipant).where(
        CallParticipant.id == participant_id, CallParticipant.session_id == session_id,
    ))
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    if user.role != UserRole.admin and participant.user_id != user.id:
        raise HTTPException(status_code=403, detail="Participant belongs to another operator")


@router.get("")
async def list_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    call_status: CallStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(Call)
    if call_status:
        q = q.where(Call.call_status == call_status)
    q = q.order_by(Call.created_at.desc())
    total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    result = await session.execute(q.offset((page - 1) * page_size).limit(page_size))
    calls = result.scalars().all()
    session_ids = {}
    provider_ids = [call.provider_call_id for call in calls if call.provider_call_id]
    if provider_ids:
        matched = await session.execute(select(SophiaSession).where(
            SophiaSession.channel_metadata["call_sid"].astext.in_(provider_ids)
        ))
        for conversation in matched.scalars():
            sid = conversation.channel_metadata["call_sid"]
            session_ids.setdefault(sid, []).append(str(conversation.id))
    return {
        "items": [
            {
                "id": str(c.id),
                "sophia_session_id": session_ids[c.provider_call_id][0] if len(session_ids.get(c.provider_call_id, [])) == 1 else None,
                "lead_id": str(c.lead_id) if c.lead_id else None,
                "workflow_id": str(c.workflow_id) if c.workflow_id else None,
                "call_status": c.call_status.value,
                "provider": c.provider.value,
                "duration_seconds": c.duration_seconds,
                "started_at": c.started_at.isoformat() if c.started_at else None,
                "ended_at": c.ended_at.isoformat() if c.ended_at else None,
                "recording_url": c.recording_url,
                "created_at": c.created_at.isoformat(),
            }
            for c in calls
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.post("", response_model=CallSessionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission(Permission.CALLS_INITIATE))])
async def create_session(
    body: CallSessionCreate,
    session: AsyncSession = Depends(get_session),
) -> CallSessionResponse:
    rt = CallSessionRuntime(session)
    call_session = await rt.create_session(call_id=body.call_id)
    return CallSessionResponse.model_validate(call_session)


@router.get("/{session_id}", response_model=CallSessionResponse)
async def get_session_detail(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CallSessionResponse:
    repo = CallSessionRepository(session)
    call_session = await repo.get_by_id_or_raise(session_id)
    return CallSessionResponse.model_validate(call_session)


@router.post("/{session_id}/complete", response_model=CallSessionResponse, dependencies=[Depends(require_permission(Permission.CALLS_INITIATE))])
async def complete_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CallSessionResponse:
    try:
        rt = CallSessionRuntime(session)
        call_session = await rt.complete_session(session_id)
        return CallSessionResponse.model_validate(call_session)
    except CallSessionTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{session_id}/fail", response_model=CallSessionResponse, dependencies=[Depends(require_permission(Permission.CALLS_INITIATE))])
async def fail_session(
    session_id: UUID,
    reason: str = Query(""),
    session: AsyncSession = Depends(get_session),
) -> CallSessionResponse:
    try:
        rt = CallSessionRuntime(session)
        call_session = await rt.fail_session(session_id, reason=reason)
        return CallSessionResponse.model_validate(call_session)
    except CallSessionTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/{session_id}/join",
    response_model=CallParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def join_session(
    session_id: UUID,
    body: CallParticipantJoin,
    current_user=Depends(require_permission(Permission.CALLS_INITIATE)),
    session: AsyncSession = Depends(get_session),
) -> CallParticipantResponse:
    from models.enums import ParticipantRole
    if body.user_id not in (None, current_user.id) or body.role != ParticipantRole.operator:
        raise HTTPException(status_code=403, detail="Participant identity and role must match the authenticated operator")
    try:
        rt = CallSessionRuntime(session)
        _, participant = await rt.join(
            session_id=session_id,
            role=body.role,
            user_id=current_user.id,
            connection_id=body.connection_id,
        )
        return CallParticipantResponse.model_validate(participant)
    except CallSessionTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/{session_id}/participants/{participant_id}/leave",
    response_model=CallParticipantResponse,
)
async def leave_session(
    session_id: UUID,
    participant_id: UUID,
    current_user=Depends(require_permission(Permission.CALLS_INITIATE)),
    session: AsyncSession = Depends(get_session),
) -> CallParticipantResponse:
    await _require_participant_actor(session, session_id, participant_id, current_user)
    rt = CallSessionRuntime(session)
    participant = await rt.leave(session_id, participant_id)
    return CallParticipantResponse.model_validate(participant)


@router.post(
    "/{session_id}/participants/{participant_id}/heartbeat",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def heartbeat(
    session_id: UUID,
    participant_id: UUID,
    current_user=Depends(require_permission(Permission.CALLS_INITIATE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _require_participant_actor(session, session_id, participant_id, current_user)
    rt = CallSessionRuntime(session)
    await rt.heartbeat(session_id, participant_id)


@router.get("/{session_id}/participants", response_model=list[CallParticipantResponse])
async def list_participants(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[CallParticipantResponse]:
    repo = CallSessionRepository(session)
    await repo.get_by_id_or_raise(session_id)
    p_repo = CallParticipantRepository(session)
    participants = await p_repo.get_by_session(session_id)
    return [CallParticipantResponse.model_validate(p) for p in participants]


@router.get("/{session_id}/events", response_model=dict)
async def list_session_events(
    session_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> dict:
    repo = CallSessionRepository(session)
    await repo.get_by_id_or_raise(session_id)
    event_repo = CallEventRepository(session)
    result = await event_repo.get_by_session(session_id, page=page, page_size=page_size)
    return {
        "items": [CallEventResponse.model_validate(e).model_dump() for e in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/{session_id}/replay", response_model=dict)
async def replay_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = CallSessionRuntime(session)
    result = await rt.replay(session_id)
    return {
        "session_id": str(result.session_id),
        "replayed_events": result.replayed_events,
        "final_status": result.final_status,
        "participant_count": result.participant_count,
    }


@router.get("/{session_id}/presence", response_model=list[ConnectionStateResponse])
async def get_presence(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ConnectionStateResponse]:
    repo = CallSessionRepository(session)
    await repo.get_by_id_or_raise(session_id)
    presence_rt = PresenceRuntime(session)
    records = await presence_rt.get_presence(session_id)
    return [
        ConnectionStateResponse(
            participant_id=r.participant_id,
            session_id=r.session_id,
            participant_status=r.status,
            connection_id=r.connection_id,
            last_heartbeat_at=r.last_heartbeat_at,
            is_stale=not r.is_online and r.status == "joined",
        )
        for r in records
    ]
