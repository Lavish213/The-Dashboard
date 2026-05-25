from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from approvals.engine import ApprovalEngine, ApprovalEngineError
from db.session import get_session
from models.enums import ApprovalType
from repositories.approval import ApprovalRepository
from schemas.approval import ApprovalCreate, ApprovalResolve, ApprovalResponse
from security.auth import get_current_active_user
from workflows.approvals import ApprovalGateError
from workflows.transitions import TransitionError

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.post("/request", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
async def request_approval(
    body: ApprovalCreate,
    session: AsyncSession = Depends(get_session),
) -> ApprovalResponse:
    try:
        engine = ApprovalEngine(session)
        approval = await engine.request(
            workflow_id=body.workflow_id,
            approval_type=body.approval_type,
            requested_by=body.requested_by,
            risk_level=body.risk_level,
            expires_at=body.expires_at,
        )
        return ApprovalResponse.model_validate(approval)
    except (TransitionError, ApprovalGateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{approval_id}/resolve", response_model=ApprovalResponse)
async def resolve_approval(
    approval_id: UUID,
    body: ApprovalResolve,
    session: AsyncSession = Depends(get_session),
) -> ApprovalResponse:
    from models.enums import ApprovalStatus
    if body.approval_status not in (ApprovalStatus.approved, ApprovalStatus.rejected):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="approval_status must be 'approved' or 'rejected'",
        )
    try:
        engine = ApprovalEngine(session)
        approval = await engine.resolve(
            approval_id=approval_id,
            resolved_by=body.resolved_by,
            approved=(body.approval_status == ApprovalStatus.approved),
            notes=body.resolution_notes or "",
        )
        return ApprovalResponse.model_validate(approval)
    except (ApprovalGateError, ApprovalEngineError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# NOTE: literal routes declared before /{approval_id} to prevent path capture
@router.get("/pending", response_model=dict)
async def list_pending_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    approval_type: ApprovalType | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    repo = ApprovalRepository(session)
    if approval_type is not None:
        result = await repo.get_pending_by_type(approval_type, page=page, page_size=page_size)
    else:
        result = await repo.get_pending(page=page, page_size=page_size)
    return {
        "items": [ApprovalResponse.model_validate(a).model_dump() for a in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/workflow/{workflow_id}", response_model=list[ApprovalResponse])
async def list_workflow_approvals(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ApprovalResponse]:
    repo = ApprovalRepository(session)
    approvals = await repo.get_by_workflow(workflow_id)
    return [ApprovalResponse.model_validate(a) for a in approvals]


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ApprovalResponse:
    repo = ApprovalRepository(session)
    approval = await repo.get_by_id_or_raise(approval_id)
    return ApprovalResponse.model_validate(approval)
