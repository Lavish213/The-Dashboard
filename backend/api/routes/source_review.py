from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from security.permissions import require_permission
from security.rbac import Permission
from services.source_commands import destination

router = APIRouter(dependencies=[Depends(require_permission(Permission.LEADS_READ))])


async def source_request(method, path, body=None):
    url, secret, _ = destination()
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.request(
                method,
                url + path,
                json=body,
                headers={"X-Source-Command-Secret": secret},
            )
        if not response.is_success:
            raise HTTPException(
                409 if response.status_code in {409, 422} else 503,
                "Source review unavailable or rejected",
            )
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid source response")
        return data
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(503, "Source review unavailable") from error


@router.get("/candidates")
async def candidates(page: int = Query(1, ge=1, le=100000)):
    return await source_request("GET", "/api/operations/candidates?page=" + str(page))


class CandidateReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(dismissed|linked_to_reviewed_lead)$")
    reason: str = Field(min_length=10, max_length=1000)
    fingerprint: str = Field(min_length=64, max_length=64)
    lead_id: UUID | None = None


@router.post("/candidates/{identity}/review")
async def review(
    identity: UUID,
    body: CandidateReview,
    actor=Depends(require_permission(Permission.LEADS_WRITE)),
):
    return await source_request(
        "POST",
        "/api/operations/candidates/" + str(identity) + "/review",
        {**body.model_dump(mode="json"), "actor_id": str(actor.id)},
    )


@router.get('/workflow-review')
async def workflows():
    health = await source_request('GET', '/api/health/workflow-recovery')
    queue = await source_request('GET', '/api/health/workflow-recovery/review')
    return {**health, **queue}


class Reconciliation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: str = Field(pattern='^skipped$')
    reason: str = Field(min_length=10, max_length=1000)


@router.post('/workflow-review/{identity}/reconcile')
async def reconcile(identity: UUID, body: Reconciliation, actor=Depends(require_permission(Permission.LEADS_WRITE))):
    return await source_request('POST', '/api/health/workflow-recovery/' + str(identity) + '/reconcile', {**body.model_dump(), 'actor_id': str(actor.id)})
