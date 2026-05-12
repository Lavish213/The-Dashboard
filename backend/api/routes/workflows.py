from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.enums import AuditActorType
from schemas.workflow import WorkflowCreate, WorkflowResponse
from workflows.persistence import WorkflowEventRepository, WorkflowRepository
from workflows.recovery import WorkflowRecovery
from workflows.runtime import WorkflowRuntime
from workflows.transitions import TransitionError

router = APIRouter()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreate,
    session: AsyncSession = Depends(get_session),
) -> WorkflowResponse:
    runtime = WorkflowRuntime(session)
    workflow = await runtime.start(
        workflow_type=body.workflow_type,
        lead_id=body.lead_id,
        initiated_by=body.initiated_by,
        actor_type=AuditActorType.user,
    )
    return WorkflowResponse.model_validate(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> WorkflowResponse:
    repo = WorkflowRepository(session)
    workflow = await repo.get_by_id_or_raise(workflow_id)
    return WorkflowResponse.model_validate(workflow)


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------

@router.post("/{workflow_id}/pause", response_model=WorkflowResponse)
async def pause_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> WorkflowResponse:
    try:
        runtime = WorkflowRuntime(session)
        workflow = await runtime.pause(workflow_id, actor_type=AuditActorType.user)
        return WorkflowResponse.model_validate(workflow)
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{workflow_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> WorkflowResponse:
    try:
        runtime = WorkflowRuntime(session)
        workflow = await runtime.resume(workflow_id, actor_type=AuditActorType.user)
        return WorkflowResponse.model_validate(workflow)
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{workflow_id}/complete", response_model=WorkflowResponse)
async def complete_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> WorkflowResponse:
    try:
        runtime = WorkflowRuntime(session)
        workflow = await runtime.complete(workflow_id, actor_type=AuditActorType.system)
        return WorkflowResponse.model_validate(workflow)
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{workflow_id}/cancel", response_model=WorkflowResponse)
async def cancel_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> WorkflowResponse:
    try:
        runtime = WorkflowRuntime(session)
        workflow = await runtime.cancel(workflow_id, actor_type=AuditActorType.user)
        return WorkflowResponse.model_validate(workflow)
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@router.get("/{workflow_id}/events")
async def get_workflow_events(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    repo = WorkflowRepository(session)
    await repo.get_by_id_or_raise(workflow_id)  # 404 guard
    events_repo = WorkflowEventRepository(session)
    events = await events_repo.get_by_workflow(workflow_id)
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "payload": e.payload,
            "actor_type": e.actor_type,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "correlation_id": str(e.correlation_id),
            "causation_id": str(e.causation_id) if e.causation_id else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

@router.post("/{workflow_id}/recover", response_model=WorkflowResponse)
async def recover_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> WorkflowResponse:
    try:
        recovery = WorkflowRecovery(session)
        workflow = await recovery.resume_failed(workflow_id)
        return WorkflowResponse.model_validate(workflow)
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{workflow_id}/replay")
async def replay_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    recovery = WorkflowRecovery(session)
    result = await recovery.replay(workflow_id)
    return {
        "workflow_id": str(result.workflow_id),
        "replayed_events": result.replayed_events,
        "final_status": result.final_status,
        "final_step": result.final_step,
    }
