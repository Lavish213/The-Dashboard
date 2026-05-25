import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import models.transcript_chunk
import models.transcript_segment
import models.transcript_event
import models.transcript_stream
import models.transcript_checkpoint
import models.sophia_session
import models.sophia_turn
import models.sophia_event
import models.call_session
import models.call_event
import models.call_participant
import models.workflow_event
import models.workflow_checkpoint
import models.workflow_snapshot
import models.workflow_lease

from db.session import async_session_factory
from models.call import Call
from models.enums import (
    CallProvider,
    CallStatus,
    LeadSource,
    LeadStatus,
    WorkflowStatus,
    WorkflowType,
)
from models.lead import Lead
from models.workflow import Workflow


async def seed():
    async with async_session_factory() as session:
        leads_data = [
            ("Marcus Williams", "209-555-0147", LeadStatus.new, LeadSource.direct, 8),
            ("Sandra Pierce", "209-555-0192", LeadStatus.new, LeadSource.referral, 6),
            ("David Torres", "209-555-0231", LeadStatus.new, LeadSource.organic, 4),
            ("Jennifer Davis", "209-555-0291", LeadStatus.contacted, LeadSource.direct, 9),
            ("Robert Chen", "209-555-0438", LeadStatus.contacted, LeadSource.referral, 7),
            ("Patricia Moore", "209-555-0512", LeadStatus.contacted, LeadSource.organic, 5),
            ("James Wilson", "209-555-0783", LeadStatus.qualified, LeadSource.direct, 8),
            ("Linda Martinez", "209-555-0624", LeadStatus.qualified, LeadSource.referral, 9),
            ("Thomas Anderson", "209-555-0847", LeadStatus.qualified, LeadSource.direct, 7),
            ("Barbara Jackson", "209-555-0193", LeadStatus.converted, LeadSource.direct, 10),
            ("Charles White", "209-555-0374", LeadStatus.converted, LeadSource.referral, 9),
            ("Margaret Harris", "209-555-0582", LeadStatus.converted, LeadSource.organic, 8),
            ("Christopher Lewis", "209-555-0719", LeadStatus.dead, LeadSource.organic, 2),
            ("Dorothy Robinson", "209-555-0836", LeadStatus.dead, LeadSource.paid, 1),
        ]

        leads = []
        for i, (name, phone, status, source, score) in enumerate(leads_data):
            lead = Lead(
                full_name=name,
                phone=phone,
                lead_status=status,
                lead_source=source,
                ai_score=score,
                last_contacted_at=datetime.now(UTC) - timedelta(hours=i * 3),
            )
            session.add(lead)
            leads.append(lead)

        await session.flush()
        print(f"seeded {len(leads)} leads")

        calls_data = [
            (leads[0], CallStatus.connected, 167, CallProvider.retell),
            (leads[3], CallStatus.completed, 334, CallProvider.retell),
            (leads[4], CallStatus.completed, 130, CallProvider.retell),
            (leads[5], CallStatus.no_answer, None, CallProvider.retell),
            (leads[6], CallStatus.completed, 442, CallProvider.retell),
            (leads[7], CallStatus.completed, 290, CallProvider.retell),
            (leads[8], CallStatus.voicemail, 48, CallProvider.retell),
            (leads[9], CallStatus.completed, 520, CallProvider.retell),
            (leads[10], CallStatus.completed, 380, CallProvider.retell),
            (leads[1], CallStatus.no_answer, None, CallProvider.retell),
            (leads[2], CallStatus.no_answer, None, CallProvider.retell),
            (leads[11], CallStatus.completed, 610, CallProvider.retell),
        ]

        for lead, status, duration, provider in calls_data:
            started = datetime.now(UTC) - timedelta(hours=12)
            call = Call(
                lead_id=lead.id,
                provider=provider,
                call_status=status,
                duration_seconds=duration,
                started_at=started,
                ended_at=started + timedelta(seconds=duration) if duration else None,
            )
            session.add(call)

        await session.flush()
        print(f"seeded {len(calls_data)} calls")

        workflow_types = [
            (leads[3], WorkflowType.outreach, WorkflowStatus.completed),
            (leads[4], WorkflowType.qualification, WorkflowStatus.active),
            (leads[6], WorkflowType.follow_up, WorkflowStatus.active),
            (leads[7], WorkflowType.closing, WorkflowStatus.active),
            (leads[9], WorkflowType.closing, WorkflowStatus.completed),
            (leads[10], WorkflowType.closing, WorkflowStatus.completed),
            (leads[12], WorkflowType.outreach, WorkflowStatus.failed),
            (leads[13], WorkflowType.qualification, WorkflowStatus.cancelled),
        ]

        for lead, wf_type, wf_status in workflow_types:
            wf = Workflow(
                workflow_type=wf_type,
                workflow_status=wf_status,
                lead_id=lead.id,
                correlation_id=uuid.uuid4(),
                current_step="completed" if wf_status == WorkflowStatus.completed else "active",
            )
            session.add(wf)

        await session.flush()
        print(f"seeded {len(workflow_types)} workflows")

        await session.commit()
        print("done — all data committed")


asyncio.run(seed())