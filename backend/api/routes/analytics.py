from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.call import Call
from models.enums import CallStatus, LeadStatus, WorkflowStatus
from models.lead import Lead
from models.workflow import Workflow
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("")
async def get_analytics(
    session: AsyncSession = Depends(get_session),
) -> dict:
    async def count(model, *conditions):
        q = select(func.count()).select_from(model)
        if conditions:
            q = q.where(*conditions)
        return (await session.execute(q)).scalar_one()

    total_leads = await count(Lead)
    leads_new = await count(Lead, Lead.lead_status == LeadStatus.new)
    leads_contacted = await count(Lead, Lead.lead_status == LeadStatus.contacted)
    leads_qualified = await count(Lead, Lead.lead_status == LeadStatus.qualified)
    leads_converted = await count(Lead, Lead.lead_status == LeadStatus.converted)
    leads_dead = await count(Lead, Lead.lead_status == LeadStatus.dead)

    total_calls = await count(Call)
    calls_completed = await count(Call, Call.call_status == CallStatus.completed)
    calls_no_answer = await count(Call, Call.call_status == CallStatus.no_answer)
    calls_voicemail = await count(Call, Call.call_status == CallStatus.voicemail)
    calls_failed = await count(Call, Call.call_status == CallStatus.failed)

    total_workflows = await count(Workflow)
    workflows_active = await count(Workflow, Workflow.workflow_status == WorkflowStatus.active)
    workflows_completed = await count(Workflow, Workflow.workflow_status == WorkflowStatus.completed)
    workflows_failed = await count(Workflow, Workflow.workflow_status == WorkflowStatus.failed)

    avg_duration = (await session.execute(
        select(func.avg(Call.duration_seconds)).where(
            Call.call_status == CallStatus.completed,
            Call.duration_seconds.isnot(None),
        )
    )).scalar_one()

    return {
        "leads": {
            "total": total_leads,
            "by_status": {
                "new": leads_new,
                "contacted": leads_contacted,
                "qualified": leads_qualified,
                "converted": leads_converted,
                "dead": leads_dead,
            },
        },
        "calls": {
            "total": total_calls,
            "completed": calls_completed,
            "no_answer": calls_no_answer,
            "voicemail": calls_voicemail,
            "failed": calls_failed,
            "contact_rate": round(calls_completed / total_calls * 100, 1) if total_calls else 0,
            "avg_duration_seconds": round(avg_duration) if avg_duration else 0,
        },
        "workflows": {
            "total": total_workflows,
            "active": workflows_active,
            "completed": workflows_completed,
            "failed": workflows_failed,
        },
    }