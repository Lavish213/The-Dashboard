import asyncio
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from approvals.engine import ApprovalEngine
from models.approval import Approval
from models.enums import (
    ApprovalStatus,
    ApprovalType,
    UserRole,
    UserStatus,
    WorkflowStatus,
    WorkflowType,
)
from models.user import User
from models.workflow import Workflow
from models.workflow_event import WorkflowEvent
from repositories.approval import ApprovalRepository
from workflows.approvals import ApprovalGateError, WorkflowApprovalGate


async def pending(db, expires=None, status=ApprovalStatus.pending):
    workflow = Workflow(workflow_type=WorkflowType.follow_up, workflow_status=WorkflowStatus.paused)
    db.add(workflow)
    await db.flush()
    approval = Approval(workflow_id=workflow.id, approval_type=ApprovalType.outreach, approval_status=status, expires_at=expires)
    db.add(approval)
    await db.flush()
    return workflow, approval


async def test_expired_approval_cannot_resume_workflow(db):
    workflow, approval = await pending(db, datetime.now(UTC)-timedelta(minutes=1))
    with pytest.raises(ApprovalGateError, match='expired'):
        await WorkflowApprovalGate(db).resolve(approval.id, None, True)
    assert approval.approval_status == ApprovalStatus.pending
    assert workflow.workflow_status == WorkflowStatus.paused


@pytest.mark.parametrize('status', [WorkflowStatus.completed, WorkflowStatus.failed, WorkflowStatus.cancelled, WorkflowStatus.active])
async def test_approval_cannot_resurrect_changed_workflow(db, status):
    workflow, approval = await pending(db)
    workflow.workflow_status = status
    await db.flush()
    with pytest.raises(ApprovalGateError, match='no longer paused'):
        await WorkflowApprovalGate(db).resolve(approval.id, None, True)
    assert approval.approval_status == ApprovalStatus.pending
    assert workflow.workflow_status == status


async def test_escalated_approval_remains_in_pending_operator_queue(db):
    _, approval = await pending(db, status=ApprovalStatus.escalated)
    page = await ApprovalRepository(db).get_pending()
    assert approval.id in [row.id for row in page.items]
    typed = await ApprovalRepository(db).get_pending_by_type(ApprovalType.outreach)
    assert approval.id in [row.id for row in typed.items]
    assert await WorkflowApprovalGate(db).has_pending_approval(approval.workflow_id)


async def test_failed_commit_never_broadcasts_approval_success(db, monkeypatch):
    from approvals import engine
    _, approval = await pending(db)
    publish = AsyncMock()
    monkeypatch.setattr(engine.broadcast_service, 'publish', publish)
    monkeypatch.setattr(db, 'commit', AsyncMock(side_effect=RuntimeError('synthetic commit loss')))
    with pytest.raises(RuntimeError, match='commit loss'):
        await ApprovalEngine(db).resolve(approval.id, None, True, commit_before_publish=True)
    publish.assert_not_awaited()


async def test_twenty_concurrent_resolvers_produce_one_state_change_and_one_audit():
    engine = create_async_engine(os.environ['TEST_DATABASE_URL'])
    user_id, workflow_id, approval_id = uuid4(), uuid4(), uuid4()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add(User(id=user_id, email=f'{user_id}@example.invalid', full_name='Synthetic reviewer', role=UserRole.reviewer, status=UserStatus.active))
            session.add(Workflow(id=workflow_id, workflow_type=WorkflowType.follow_up, workflow_status=WorkflowStatus.paused))
            await session.flush()
            session.add(Approval(id=approval_id, workflow_id=workflow_id, approval_type=ApprovalType.outreach, approval_status=ApprovalStatus.pending))
            await session.commit()
        async def resolve():
            async with AsyncSession(engine, expire_on_commit=False) as session:
                try:
                    await WorkflowApprovalGate(session).resolve(approval_id, user_id, True)
                    await session.commit()
                    return True
                except ApprovalGateError:
                    await session.rollback()
                    return False
        results = await asyncio.gather(*(resolve() for _ in range(20)))
        assert sum(results) == 1
        async with AsyncSession(engine) as session:
            assert (await session.get(Approval, approval_id)).resolved_by == user_id
            count = await session.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.workflow_id == workflow_id))
            assert count == 1
    finally:
        async with engine.begin() as connection:
            await connection.execute(delete(WorkflowEvent).where(WorkflowEvent.workflow_id == workflow_id))
            await connection.execute(delete(Approval).where(Approval.id == approval_id))
            await connection.execute(delete(Workflow).where(Workflow.id == workflow_id))
            await connection.execute(delete(User).where(User.id == user_id))
        await engine.dispose()


async def test_workflow_expiry_blocks_still_pending_approval(db):
    workflow, approval = await pending(db)
    workflow.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db.flush()
    with pytest.raises(ApprovalGateError, match='workflow authorization has expired'):
        await WorkflowApprovalGate(db).resolve(approval.id, None, True)
    assert approval.approval_status == ApprovalStatus.pending


async def test_expired_escalated_approval_is_processed_and_removed_from_queue(db):
    from approvals.expiry import ApprovalExpiryRuntime
    _, approval = await pending(db, datetime.now(UTC)-timedelta(minutes=1), ApprovalStatus.escalated)
    result = await ApprovalExpiryRuntime(db).expire_pending()
    assert approval.id in result.approval_ids
    assert approval.approval_status == ApprovalStatus.expired
    assert approval.id not in [row.id for row in (await ApprovalRepository(db).get_pending()).items]


async def test_expiry_rechecks_locked_status_before_overwriting_resolved_decision(db, monkeypatch):
    from approvals.expiry import ApprovalExpiryRuntime
    _, approval = await pending(db)
    await WorkflowApprovalGate(db).resolve(approval.id, None, True)
    runtime = ApprovalExpiryRuntime(db)
    monkeypatch.setattr(runtime._repo, 'get_expired_pending', AsyncMock(return_value=[approval]))
    result = await runtime.expire_pending()
    assert result.expired_count == 0
    assert approval.approval_status == ApprovalStatus.approved
