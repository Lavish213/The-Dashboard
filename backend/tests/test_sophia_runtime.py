"""
Phase 12 — Sophia Runtime tests.

Covers:
- SophiaSession contracts + state machine
- SophiaTurn lifecycle
- SophiaInterruptionRuntime
- SophiaHandoffRuntime
- SophiaToolBoundary (tool permission checks)
- SophiaContextAdapter (static, no DB)
- SophiaTranscriptAdapter (static, no DB)
- SophiaAuditRuntime
- SophiaCheckpointRuntime
- SophiaCancellationRuntime
- SophiaMetricsRuntime
- SophiaReplayRuntime
- SophiaProviderBoundary contracts
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from models.enums import (
    SophiaChannelType,
    SophiaEventType,
    SophiaHandoffStatus,
    SophiaInterruptionReason,
    SophiaSessionStatus,
    SophiaTurnStatus,
)
from sophia.adapters import SophiaContextAdapter, SophiaTranscriptAdapter
from sophia.audit import SophiaAuditRuntime
from sophia.cancellation import SophiaCancellationRuntime
from sophia.checkpoint import SophiaCheckpointRuntime
from sophia.contracts import (
    SophiaCancellationRequest,
    SophiaContextInput,
    SophiaHandoffRequest,
    SophiaInterruption,
    SophiaMetrics,
    SophiaProviderBoundary,
    SophiaReplayFrame,
    SophiaSessionRecord,
    SophiaSessionSpec,
    SophiaToolPermissionRequest,
    SophiaTurnInput,
)
from sophia.handoff import SophiaHandoffRuntime
from sophia.interruption import SophiaInterruptionRuntime
from sophia.metrics import SophiaMetricsRuntime
from sophia.replay import SophiaReplayRuntime
from sophia.session import SophiaSessionError, SophiaSessionRuntime
from sophia.turn import SophiaTurnError, SophiaTurnRuntime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_spec(**kwargs) -> SophiaSessionSpec:
    return SophiaSessionSpec(
        session_key=kwargs.pop("session_key", f"sess-{uuid.uuid4()}"),
        channel=kwargs.pop("channel", SophiaChannelType.text),
        **kwargs,
    )


def _turn_input(session_id: uuid.UUID, turn_index: int = 0, **kwargs) -> SophiaTurnInput:
    return SophiaTurnInput(
        session_id=session_id,
        turn_index=turn_index,
        input_payload=kwargs.pop("input_payload", {"text": "hello"}),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Session contracts
# ---------------------------------------------------------------------------

class TestSophiaSessionContracts:
    def test_session_spec_frozen(self):
        spec = _session_spec(session_key="frozen-test")
        with pytest.raises((AttributeError, TypeError)):
            spec.session_key = "mutated"  # type: ignore[misc]

    def test_session_record_frozen(self):
        rec = SophiaSessionRecord(
            session_id=uuid.uuid4(),
            session_key="k",
            status=SophiaSessionStatus.active,
            channel=SophiaChannelType.text,
            workflow_id=None,
            lead_id=None,
            initiated_by=None,
            token_budget=8192,
            tokens_used=0,
            turn_count=0,
            max_turns=50,
            channel_metadata={},
            checkpoint_state=None,
            created_at=datetime.now(UTC),
        )
        with pytest.raises((AttributeError, TypeError)):
            rec.status = SophiaSessionStatus.completed  # type: ignore[misc]

    def test_provider_boundary_contract(self):
        pb = SophiaProviderBoundary(
            channel=SophiaChannelType.text,
            provider_name="text",
            supports_interruption=False,
            supports_barge_in=False,
            max_utterance_tokens=2048,
        )
        assert pb.channel == SophiaChannelType.text
        assert not pb.supports_barge_in

    def test_voice_provider_boundary_contract(self):
        pb = SophiaProviderBoundary(
            channel=SophiaChannelType.voice,
            provider_name="voice_stub",
            supports_interruption=True,
            supports_barge_in=True,
            max_utterance_tokens=512,
        )
        assert pb.supports_barge_in is True


# ---------------------------------------------------------------------------
# Session state machine
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaSessionRuntime:
    async def test_create_session(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="create-1", channel=SophiaChannelType.text)
        rec = await rt.create(spec)
        assert rec.status == SophiaSessionStatus.initializing
        assert rec.session_key == "create-1"
        assert rec.token_budget == 8192

    async def test_create_idempotent(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="idem-sess")
        r1 = await rt.create(spec)
        r2 = await rt.create(spec)
        assert r1.session_id == r2.session_id

    async def test_activate_session(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="activate-1")
        rec = await rt.create(spec)
        activated = await rt.activate(rec.session_id)
        assert activated.status == SophiaSessionStatus.active

    async def test_complete_session(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="complete-1")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        completed = await rt.complete(rec.session_id)
        assert completed.status == SophiaSessionStatus.completed

    async def test_cancel_session(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="cancel-1")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        cancelled = await rt.cancel(rec.session_id, reason="test cancel")
        assert cancelled.status == SophiaSessionStatus.cancelled

    async def test_fail_session(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="fail-1")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        failed = await rt.fail(rec.session_id, error="runtime error")
        assert failed.status == SophiaSessionStatus.failed

    async def test_interrupt_and_resume(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="interrupt-resume-1")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        interrupted = await rt.interrupt(rec.session_id, reason="barge-in")
        assert interrupted.status == SophiaSessionStatus.interrupted
        resumed = await rt.resume(rec.session_id)
        assert resumed.status == SophiaSessionStatus.active

    async def test_invalid_transition_raises(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="invalid-trans-1")
        rec = await rt.create(spec)
        # initializing → completed is invalid
        with pytest.raises(SophiaSessionError):
            await rt.complete(rec.session_id)

    async def test_get_by_key(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="get-by-key-1")
        await rt.create(spec)
        found = await rt.get_by_key("get-by-key-1")
        assert found is not None
        assert found.session_key == "get-by-key-1"

    async def test_get_missing_returns_none(self, db):
        rt = SophiaSessionRuntime(db)
        found = await rt.get(uuid.uuid4())
        assert found is None

    async def test_session_with_workflow_id(self, db):
        rt = SophiaSessionRuntime(db)
        wf_id = uuid.uuid4()
        spec = _session_spec(session_key="wf-sess-1", workflow_id=wf_id)
        rec = await rt.create(spec)
        assert rec.workflow_id == wf_id

    async def test_session_with_lead_id(self, db):
        rt = SophiaSessionRuntime(db)
        lead_id = uuid.uuid4()
        spec = _session_spec(session_key="lead-sess-1", lead_id=lead_id)
        rec = await rt.create(spec)
        assert rec.lead_id == lead_id

    async def test_handoff_flow(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="handoff-1")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        operator_id = uuid.uuid4()
        awaiting = await rt.request_handoff(
            rec.session_id, handoff_to=operator_id, reason="user request"
        )
        assert awaiting.status == SophiaSessionStatus.awaiting_handoff

        handed = await rt.accept_handoff(rec.session_id, actor_id=operator_id)
        assert handed.status == SophiaSessionStatus.handed_off

    async def test_session_emits_started_event(self, db):
        from repositories.sophia_event import SophiaEventRepository
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="event-start-1")
        rec = await rt.create(spec)
        events_repo = SophiaEventRepository(db)
        events = await events_repo.get_for_session(rec.session_id)
        assert any(e.event_type == SophiaEventType.session_started for e in events)

    async def test_session_emits_completed_event(self, db):
        from repositories.sophia_event import SophiaEventRepository
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="event-complete-1")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        await rt.complete(rec.session_id)
        events_repo = SophiaEventRepository(db)
        events = await events_repo.get_for_session(rec.session_id)
        assert any(e.event_type == SophiaEventType.session_completed for e in events)

    async def test_cannot_activate_completed_session(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="no-reactivate-1")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        await rt.complete(rec.session_id)
        with pytest.raises(SophiaSessionError):
            await rt.activate(rec.session_id)

    async def test_cannot_cancel_completed_session(self, db):
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key="no-cancel-complete-1")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        await rt.complete(rec.session_id)
        with pytest.raises(SophiaSessionError):
            await rt.cancel(rec.session_id, reason="too late")


# ---------------------------------------------------------------------------
# Turn lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaTurnRuntime:
    async def _make_active_session(self, db) -> uuid.UUID:
        rt = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"turn-sess-{uuid.uuid4()}")
        rec = await rt.create(spec)
        await rt.activate(rec.session_id)
        return rec.session_id

    async def test_start_turn(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        inp = _turn_input(session_id, turn_index=0)
        turn = await rt.start(inp)
        assert turn.status == SophiaTurnStatus.running
        assert turn.turn_index == 0

    async def test_complete_turn(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        completed = await rt.complete(
            turn.turn_id,
            output_payload={"text": "Hello, I can help."},
            tokens_input=10,
            tokens_output=20,
        )
        assert completed.status == SophiaTurnStatus.completed
        assert completed.tokens_output == 20

    async def test_complete_updates_session_tokens(self, db):
        rt_s = SophiaSessionRuntime(db)
        rt_t = SophiaTurnRuntime(db)
        spec = _session_spec(session_key=f"token-update-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        turn = await rt_t.start(_turn_input(rec.session_id, 0))
        await rt_t.complete(
            turn.turn_id,
            output_payload={"text": "reply"},
            tokens_input=15,
            tokens_output=25,
        )
        session = await rt_s.get(rec.session_id)
        assert session.tokens_used == 40
        assert session.turn_count == 1

    async def test_interrupt_turn(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        interrupted = await rt.interrupt(
            turn.turn_id,
            reason=SophiaInterruptionReason.user_barge_in,
        )
        assert interrupted.status == SophiaTurnStatus.interrupted
        assert interrupted.interruption_reason == SophiaInterruptionReason.user_barge_in

    async def test_turn_idempotent_on_key(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        key = f"turn-key-{uuid.uuid4()}"
        inp = _turn_input(session_id, 0, turn_key=key)
        t1 = await rt.start(inp)
        t2 = await rt.start(inp)
        assert t1.turn_id == t2.turn_id

    async def test_await_approval(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        approval_id = uuid.uuid4()
        gated = await rt.await_approval(turn.turn_id, approval_id=approval_id)
        assert gated.status == SophiaTurnStatus.awaiting_approval
        assert gated.approval_id == approval_id

    async def test_resume_after_approval(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        await rt.await_approval(turn.turn_id, approval_id=uuid.uuid4())
        resumed = await rt.resume_after_approval(turn.turn_id)
        assert resumed.status == SophiaTurnStatus.running

    async def test_cancel_turn(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        cancelled = await rt.cancel(turn.turn_id)
        assert cancelled.status == SophiaTurnStatus.cancelled

    async def test_fail_turn(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        failed = await rt.fail(turn.turn_id, error="provider timeout")
        assert failed.status == SophiaTurnStatus.failed

    async def test_get_turns_ordered(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        for i in range(3):
            t = await rt.start(_turn_input(session_id, i))
            await rt.complete(t.turn_id, output_payload={"text": f"reply {i}"})
        turns = await rt.get_turns(session_id)
        assert [t.turn_index for t in turns] == [0, 1, 2]

    async def test_cannot_complete_cancelled_turn(self, db):
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        await rt.cancel(turn.turn_id)
        with pytest.raises(SophiaTurnError):
            await rt.complete(turn.turn_id, output_payload={})

    async def test_turn_emits_started_event(self, db):
        from repositories.sophia_event import SophiaEventRepository
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        events = await SophiaEventRepository(db).get_for_turn(turn.turn_id)
        assert any(e.event_type == SophiaEventType.turn_started for e in events)

    async def test_turn_emits_completed_event(self, db):
        from repositories.sophia_event import SophiaEventRepository
        session_id = await self._make_active_session(db)
        rt = SophiaTurnRuntime(db)
        turn = await rt.start(_turn_input(session_id, 0))
        await rt.complete(turn.turn_id, output_payload={"text": "done"})
        events = await SophiaEventRepository(db).get_for_turn(turn.turn_id)
        assert any(e.event_type == SophiaEventType.turn_completed for e in events)


# ---------------------------------------------------------------------------
# Interruption
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaInterruptionRuntime:
    async def _make_active(self, db):
        rt_s = SophiaSessionRuntime(db)
        rt_t = SophiaTurnRuntime(db)
        spec = _session_spec(session_key=f"intr-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)
        turn = await rt_t.start(_turn_input(rec.session_id, 0))
        return rec.session_id, turn.turn_id

    async def test_barge_in(self, db):
        session_id, turn_id = await self._make_active(db)
        rt = SophiaInterruptionRuntime(db)
        result = await rt.barge_in(session_id, turn_id)
        assert result.status == SophiaTurnStatus.interrupted
        assert result.interruption_reason == SophiaInterruptionReason.user_barge_in

    async def test_timeout_interruption(self, db):
        session_id, turn_id = await self._make_active(db)
        rt = SophiaInterruptionRuntime(db)
        result = await rt.timeout(session_id, turn_id)
        assert result.interruption_reason == SophiaInterruptionReason.timeout

    async def test_governance_block(self, db):
        session_id, turn_id = await self._make_active(db)
        rt = SophiaInterruptionRuntime(db)
        result = await rt.governance_block(
            session_id, turn_id, reason="forbidden action attempted"
        )
        assert result.interruption_reason == SophiaInterruptionReason.governance_block
        assert "forbidden" in (result.interruption_notes or "")

    async def test_interrupt_turn_full(self, db):
        session_id, turn_id = await self._make_active(db)
        rt = SophiaInterruptionRuntime(db)
        interruption = SophiaInterruption(
            session_id=session_id,
            turn_id=turn_id,
            reason=SophiaInterruptionReason.cancellation,
            notes="user cancelled",
        )
        result = await rt.interrupt_turn(interruption)
        assert result.interruption_reason == SophiaInterruptionReason.cancellation

        # Session should also be interrupted
        rt_s = SophiaSessionRuntime(db)
        sess = await rt_s.get(session_id)
        assert sess.status == SophiaSessionStatus.interrupted


# ---------------------------------------------------------------------------
# Handoff
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaHandoffRuntime:
    async def test_request_and_accept_handoff(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"handoff-rt-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        operator_id = uuid.uuid4()
        rt_h = SophiaHandoffRuntime(db)
        handoff_rec = await rt_h.request(
            SophiaHandoffRequest(
                session_id=rec.session_id,
                handoff_to=operator_id,
                reason="escalate to human",
            )
        )
        assert handoff_rec.status == SophiaHandoffStatus.requested

        accepted = await rt_h.accept(rec.session_id, accepted_by=operator_id)
        assert accepted.status == SophiaHandoffStatus.accepted

        sess = await rt_s.get(rec.session_id)
        assert sess.status == SophiaSessionStatus.handed_off

    async def test_reject_handoff(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"handoff-reject-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        operator_id = uuid.uuid4()
        rt_h = SophiaHandoffRuntime(db)
        await rt_h.request(
            SophiaHandoffRequest(
                session_id=rec.session_id,
                handoff_to=operator_id,
                reason="try handoff",
            )
        )
        # Reject — session returns to active
        await rt_h.reject(rec.session_id, rejected_by=operator_id, reason="no agents available")
        sess = await rt_s.get(rec.session_id)
        assert sess.status == SophiaSessionStatus.active


# ---------------------------------------------------------------------------
# Tool permission boundary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaToolBoundary:
    async def test_safe_tool_permitted_no_policy(self, db):
        """With no active policies, safe action = permitted, no approval needed."""
        from sophia.tools import SophiaToolBoundary
        session_id = uuid.uuid4()
        turn_id = uuid.uuid4()
        rt = SophiaToolBoundary(db)
        req = SophiaToolPermissionRequest(
            session_id=session_id,
            turn_id=turn_id,
            tool_name="send_message",
            action="sophia.tool.send_message",
            risk_tier="standard",
        )
        result = await rt.check(req)
        assert result.permitted is True
        assert result.requires_approval is False

    async def test_tool_check_emits_event(self, db):
        """Tool check emits tool_permitted event."""
        from repositories.sophia_event import SophiaEventRepository
        from sophia.tools import SophiaToolBoundary
        session_id = uuid.uuid4()
        turn_id = uuid.uuid4()
        rt = SophiaToolBoundary(db)
        req = SophiaToolPermissionRequest(
            session_id=session_id,
            turn_id=turn_id,
            tool_name="lookup",
            action="sophia.tool.lookup",
            risk_tier="standard",
        )
        await rt.check(req)
        events = await SophiaEventRepository(db).get_for_session(session_id)
        assert len(events) >= 1
        assert events[0].event_type in (
            SophiaEventType.tool_permitted,
            SophiaEventType.tool_blocked,
        )


# ---------------------------------------------------------------------------
# Context adapter (static)
# ---------------------------------------------------------------------------

class TestSophiaContextAdapter:
    def test_build_assembly_input_basic(self):
        session_id = uuid.uuid4()
        inp = SophiaContextInput(
            session_id=session_id,
            turn_index=2,
            token_budget=4096,
        )
        kwargs = SophiaContextAdapter.build_assembly_input(inp)
        assert kwargs["assembly_key"] == f"sophia:{session_id}:turn:2"
        assert kwargs["token_budget"] == 4096
        assert kwargs["workflow_id"] is None

    def test_build_assembly_input_with_ids(self):
        session_id = uuid.uuid4()
        wf_id = uuid.uuid4()
        tr_id = uuid.uuid4()
        inp = SophiaContextInput(
            session_id=session_id,
            turn_index=1,
            token_budget=2048,
            workflow_id=wf_id,
            transcript_id=tr_id,
        )
        kwargs = SophiaContextAdapter.build_assembly_input(inp)
        assert kwargs["workflow_id"] == wf_id
        assert kwargs["transcript_id"] == tr_id


class TestSophiaTranscriptAdapter:
    def test_turn_to_segment_payload(self):
        session_id = uuid.uuid4()
        payload = SophiaTranscriptAdapter.turn_to_segment_payload(
            session_id=session_id,
            turn_index=3,
            output_payload={"text": "How can I help?", "confidence": 0.9},
        )
        assert payload["source"] == "sophia"
        assert payload["turn_index"] == 3
        assert payload["text"] == "How can I help?"
        assert payload["metadata"]["confidence"] == 0.9

    def test_empty_text(self):
        payload = SophiaTranscriptAdapter.turn_to_segment_payload(
            session_id=uuid.uuid4(),
            turn_index=0,
            output_payload={},
        )
        assert payload["text"] == ""


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaAuditRuntime:
    async def test_record_audit_entry(self, db):
        rt = SophiaAuditRuntime(db)
        target_id = uuid.uuid4()
        entry = await rt.record(
            action="sophia.session.created",
            target_id=target_id,
            payload={"session_key": "audit-test"},
        )
        assert entry.action == "sophia.session.created"
        assert entry.target_id == target_id

    async def test_get_for_target(self, db):
        rt = SophiaAuditRuntime(db)
        target_id = uuid.uuid4()
        await rt.record("sophia.session.created", target_id=target_id)
        await rt.record("sophia.session.completed", target_id=target_id)
        entries = await rt.get_for_target(target_id)
        assert len(entries) == 2
        assert entries[0].action == "sophia.session.created"

    async def test_multiple_targets_isolated(self, db):
        rt = SophiaAuditRuntime(db)
        t1 = uuid.uuid4()
        t2 = uuid.uuid4()
        await rt.record("a.b.c", target_id=t1)
        await rt.record("d.e.f", target_id=t2)
        entries_t1 = await rt.get_for_target(t1)
        entries_t2 = await rt.get_for_target(t2)
        assert len(entries_t1) == 1
        assert len(entries_t2) == 1


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaCheckpointRuntime:
    async def test_capture_checkpoint(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"ckpt-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        rt_c = SophiaCheckpointRuntime(db)
        ckpt = await rt_c.capture(rec.session_id, turn_index=1)
        assert ckpt.turn_index == 1
        assert ckpt.token_budget_remaining == rec.token_budget

    async def test_get_latest_checkpoint(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"ckpt-latest-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        rt_c = SophiaCheckpointRuntime(db)
        await rt_c.capture(rec.session_id, turn_index=0)
        await rt_c.capture(rec.session_id, turn_index=1)

        latest = await rt_c.get_latest(rec.session_id)
        assert latest is not None
        assert latest.turn_index == 1  # last captured

    async def test_no_checkpoint_returns_none(self, db):
        rt_c = SophiaCheckpointRuntime(db)
        result = await rt_c.get_latest(uuid.uuid4())
        assert result is None

    async def test_list_checkpoints(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"ckpt-list-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        rt_c = SophiaCheckpointRuntime(db)
        await rt_c.capture(rec.session_id, turn_index=0)
        await rt_c.capture(rec.session_id, turn_index=1)
        await rt_c.capture(rec.session_id, turn_index=2)

        checkpoints = await rt_c.list_checkpoints(rec.session_id)
        assert len(checkpoints) == 3
        assert checkpoints[0].turn_index == 0

    async def test_checkpoint_emits_event(self, db):
        from repositories.sophia_event import SophiaEventRepository
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"ckpt-event-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        rt_c = SophiaCheckpointRuntime(db)
        await rt_c.capture(rec.session_id, turn_index=0)

        events = await SophiaEventRepository(db).get_for_session(rec.session_id)
        assert any(e.event_type == SophiaEventType.checkpoint_saved for e in events)

    async def test_checkpoint_with_extra_state(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"ckpt-extra-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        rt_c = SophiaCheckpointRuntime(db)
        ckpt = await rt_c.capture(
            rec.session_id,
            turn_index=5,
            extra_state={"custom_key": "custom_value"},
        )
        assert ckpt.state_blob["custom_key"] == "custom_value"


# ---------------------------------------------------------------------------
# Cancellation / Recovery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaCancellationRuntime:
    async def test_cancel_session_only(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"cancel-rt-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        rt_c = SophiaCancellationRuntime(db)
        req = SophiaCancellationRequest(
            session_id=rec.session_id,
            reason="user closed window",
        )
        result = await rt_c.cancel(req)
        assert result.status == SophiaSessionStatus.cancelled

    async def test_cancel_with_active_turn(self, db):
        rt_s = SophiaSessionRuntime(db)
        rt_t = SophiaTurnRuntime(db)
        spec = _session_spec(session_key=f"cancel-turn-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)
        turn = await rt_t.start(_turn_input(rec.session_id, 0))

        rt_c = SophiaCancellationRuntime(db)
        req = SophiaCancellationRequest(
            session_id=rec.session_id,
            reason="session timeout",
            turn_id=turn.turn_id,
        )
        result = await rt_c.cancel(req)
        assert result.status == SophiaSessionStatus.cancelled

        # Turn should also be cancelled
        turns = await rt_t.get_turns(rec.session_id)
        assert turns[0].status == SophiaTurnStatus.cancelled

    async def test_recover_interrupted_session(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"recover-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)
        await rt_s.interrupt(rec.session_id, reason="barge-in")

        rt_c = SophiaCancellationRuntime(db)
        recovered = await rt_c.recover(rec.session_id)
        assert recovered.status == SophiaSessionStatus.active

    async def test_recover_with_checkpoint_state(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"recover-ckpt-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)
        await rt_s.interrupt(rec.session_id, reason="timeout")

        checkpoint_state = {
            "checkpoint_id": str(uuid.uuid4()),
            "turn_index": 3,
            "tokens_used": 200,
            "token_budget_remaining": 7992,
            "turn_count": 3,
            "captured_at": datetime.now(UTC).isoformat(),
        }
        rt_c = SophiaCancellationRuntime(db)
        recovered = await rt_c.recover(rec.session_id, checkpoint_state=checkpoint_state)
        assert recovered.status == SophiaSessionStatus.active

        # Checkpoint state should be restored on session row
        from repositories.sophia_session import SophiaSessionRepository
        row = await SophiaSessionRepository(db).get(rec.session_id)
        assert row.checkpoint_state["turn_index"] == 3

    async def test_cancel_emits_cancellation_event(self, db):
        from repositories.sophia_event import SophiaEventRepository
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"cancel-event-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        rt_c = SophiaCancellationRuntime(db)
        await rt_c.cancel(
            SophiaCancellationRequest(session_id=rec.session_id, reason="test")
        )
        events = await SophiaEventRepository(db).get_for_session(rec.session_id)
        assert any(e.event_type == SophiaEventType.cancellation_requested for e in events)

    async def test_recover_emits_recovery_event(self, db):
        from repositories.sophia_event import SophiaEventRepository
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"recover-event-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)
        await rt_s.interrupt(rec.session_id, reason="test")

        rt_c = SophiaCancellationRuntime(db)
        await rt_c.recover(rec.session_id)
        events = await SophiaEventRepository(db).get_for_session(rec.session_id)
        assert any(e.event_type == SophiaEventType.recovery_initiated for e in events)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaMetricsRuntime:
    async def test_metrics_empty_period(self, db):
        rt = SophiaMetricsRuntime(db)
        now = datetime.now(UTC)
        past = now - timedelta(days=365)
        future = now + timedelta(days=1)
        metrics = await rt.compute(past, future)
        assert isinstance(metrics, SophiaMetrics)
        assert metrics.total_sessions >= 0

    async def test_metrics_counts_sessions(self, db):
        rt_s = SophiaSessionRuntime(db)
        now = datetime.now(UTC)

        # Create 2 sessions, complete 1
        for i in range(2):
            spec = _session_spec(session_key=f"metrics-sess-{uuid.uuid4()}")
            rec = await rt_s.create(spec)
            await rt_s.activate(rec.session_id)
            if i == 0:
                await rt_s.complete(rec.session_id)

        rt_m = SophiaMetricsRuntime(db)
        past = now - timedelta(seconds=5)
        future = now + timedelta(seconds=60)
        metrics = await rt_m.compute(past, future)
        assert metrics.total_sessions >= 2
        assert metrics.sessions_completed >= 1

    async def test_metrics_counts_turns(self, db):
        rt_s = SophiaSessionRuntime(db)
        rt_t = SophiaTurnRuntime(db)
        now = datetime.now(UTC)

        spec = _session_spec(session_key=f"metrics-turns-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)

        t0 = await rt_t.start(_turn_input(rec.session_id, 0))
        await rt_t.complete(t0.turn_id, output_payload={"text": "r"})
        t1 = await rt_t.start(_turn_input(rec.session_id, 1))
        await rt_t.interrupt(t1.turn_id, reason=SophiaInterruptionReason.timeout)

        rt_m = SophiaMetricsRuntime(db)
        past = now - timedelta(seconds=5)
        future = now + timedelta(seconds=60)
        metrics = await rt_m.compute(past, future)
        assert metrics.total_turns >= 2
        assert metrics.turns_interrupted >= 1


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSophiaReplayRuntime:
    async def test_get_frames_ordered(self, db):
        rt_s = SophiaSessionRuntime(db)
        rt_t = SophiaTurnRuntime(db)
        spec = _session_spec(session_key=f"replay-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)
        turn = await rt_t.start(_turn_input(rec.session_id, 0))
        await rt_t.complete(turn.turn_id, output_payload={"text": "done"})

        rt_r = SophiaReplayRuntime(db)
        frames = await rt_r.get_frames(rec.session_id)
        assert len(frames) >= 2
        assert all(isinstance(f, SophiaReplayFrame) for f in frames)
        # Frames must be monotonically indexed
        for i, f in enumerate(frames):
            assert f.frame_index == i
        # All frames reference the correct session
        assert all(f.session_id == rec.session_id for f in frames)

    async def test_get_turn_frames(self, db):
        rt_s = SophiaSessionRuntime(db)
        rt_t = SophiaTurnRuntime(db)
        spec = _session_spec(session_key=f"replay-turn-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)
        turn = await rt_t.start(_turn_input(rec.session_id, 0))
        await rt_t.complete(turn.turn_id, output_payload={"text": "done"})

        rt_r = SophiaReplayRuntime(db)
        frames = await rt_r.get_turn_frames(turn.turn_id)
        assert len(frames) >= 1
        assert all(f.turn_id == turn.turn_id for f in frames)

    async def test_empty_session_no_frames(self, db):
        rt_r = SophiaReplayRuntime(db)
        frames = await rt_r.get_frames(uuid.uuid4())
        assert frames == []

    async def test_replay_event_types_in_order(self, db):
        rt_s = SophiaSessionRuntime(db)
        spec = _session_spec(session_key=f"replay-order-{uuid.uuid4()}")
        rec = await rt_s.create(spec)
        await rt_s.activate(rec.session_id)
        await rt_s.complete(rec.session_id)

        rt_r = SophiaReplayRuntime(db)
        frames = await rt_r.get_frames(rec.session_id)
        event_types = [f.event_type for f in frames]
        # session_started should come before session_completed
        assert "session_started" in event_types
        assert "session_completed" in event_types
        assert event_types.index("session_started") < event_types.index("session_completed")


# ---------------------------------------------------------------------------
# Provider boundary contracts
# ---------------------------------------------------------------------------

class TestSophiaProviderBoundary:
    def test_text_provider_boundary(self):
        pb = SophiaProviderBoundary(
            channel=SophiaChannelType.text,
            provider_name="text",
            supports_interruption=False,
            supports_barge_in=False,
            max_utterance_tokens=4096,
        )
        assert pb.channel == SophiaChannelType.text
        assert pb.provider_name == "text"
        assert not pb.supports_interruption

    def test_voice_stub_boundary(self):
        pb = SophiaProviderBoundary(
            channel=SophiaChannelType.voice,
            provider_name="voice_stub",
            supports_interruption=True,
            supports_barge_in=True,
            max_utterance_tokens=256,
            metadata={"latency_ms": 50},
        )
        assert pb.supports_barge_in
        assert pb.metadata["latency_ms"] == 50

    def test_phone_boundary_frozen(self):
        pb = SophiaProviderBoundary(
            channel=SophiaChannelType.phone,
            provider_name="phone_stub",
            supports_interruption=True,
            supports_barge_in=True,
            max_utterance_tokens=128,
        )
        with pytest.raises((AttributeError, TypeError)):
            pb.provider_name = "mutated"  # type: ignore[misc]
