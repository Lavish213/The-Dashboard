import enum


class UserRole(enum.StrEnum):
    admin = "admin"
    operator = "operator"
    reviewer = "reviewer"


class UserStatus(enum.StrEnum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class LeadStatus(enum.StrEnum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    disqualified = "disqualified"
    converted = "converted"
    dead = "dead"


class LeadSource(enum.StrEnum):
    organic = "organic"
    paid = "paid"
    referral = "referral"
    direct = "direct"
    imported = "imported"


class PropertyStatus(enum.StrEnum):
    active = "active"
    under_contract = "under_contract"
    sold = "sold"
    withdrawn = "withdrawn"


class WorkflowType(enum.StrEnum):
    outreach = "outreach"
    qualification = "qualification"
    follow_up = "follow_up"
    closing = "closing"


class WorkflowStatus(enum.StrEnum):
    pending = "pending"
    active = "active"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ApprovalType(enum.StrEnum):
    offer = "offer"
    price_reduction = "price_reduction"
    skip_trace = "skip_trace"
    outreach = "outreach"


class ApprovalStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"
    escalated = "escalated"


class RiskLevel(enum.StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TranscriptStatus(enum.StrEnum):
    created = "created"
    active = "active"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    archived = "archived"


class TranscriptSourceType(enum.StrEnum):
    call = "call"
    upload = "upload"
    realtime = "realtime"
    manual = "manual"


class TranscriptStreamType(enum.StrEnum):
    agent = "agent"
    user = "user"
    system = "system"
    mixed = "mixed"


class CallStatus(enum.StrEnum):
    initiated = "initiated"
    ringing = "ringing"
    connected = "connected"
    completed = "completed"
    failed = "failed"
    no_answer = "no_answer"
    voicemail = "voicemail"


class CallProvider(enum.StrEnum):
    twilio = "twilio"
    retell = "retell"
    bland = "bland"
    signalwire = "signalwire"


class DecisionType(enum.StrEnum):
    qualification = "qualification"
    recommendation = "recommendation"
    extraction = "extraction"
    scoring = "scoring"


class RealtimeSessionStatus(enum.StrEnum):
    connected = "connected"
    disconnected = "disconnected"
    expired = "expired"


class NotificationType(enum.StrEnum):
    approval_required = "approval_required"
    workflow_update = "workflow_update"
    system_alert = "system_alert"
    lead_activity = "lead_activity"


class AuditActorType(enum.StrEnum):
    user = "user"
    system = "system"
    ai = "ai"


class CallSessionStatus(enum.StrEnum):
    waiting = "waiting"
    active = "active"
    completed = "completed"
    failed = "failed"


class ParticipantRole(enum.StrEnum):
    operator = "operator"
    lead = "lead"
    observer = "observer"


class ParticipantStatus(enum.StrEnum):
    joined = "joined"
    left = "left"
    reconnecting = "reconnecting"
    dropped = "dropped"


class LeaseStatus(enum.StrEnum):
    active = "active"
    released = "released"
    expired = "expired"


class TranscriptStreamStatus(enum.StrEnum):
    pending = "pending"
    active = "active"
    completed = "completed"
    interrupted = "interrupted"
    cancelled = "cancelled"
    failed = "failed"


class AIExecutionStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    awaiting_approval = "awaiting_approval"


class AIProviderType(enum.StrEnum):
    anthropic = "anthropic"
    openai = "openai"
    bedrock = "bedrock"
    noop = "noop"


class AITaskType(enum.StrEnum):
    inference = "inference"
    extraction = "extraction"
    scoring = "scoring"
    tool_call = "tool_call"
    classification = "classification"


class ContextLayerType(enum.StrEnum):
    system = "system"
    workflow = "workflow"
    transcript = "transcript"
    ai_execution = "ai_execution"
    user = "user"


class ContextWindowStrategy(enum.StrEnum):
    truncate_oldest = "truncate_oldest"
    truncate_lowest_priority = "truncate_lowest_priority"
    truncate_largest = "truncate_largest"
    fail_on_overflow = "fail_on_overflow"


class ContextSnapshotStatus(enum.StrEnum):
    active = "active"
    archived = "archived"
    expired = "expired"


class GovernancePolicyStatus(enum.StrEnum):
    active = "active"
    inactive = "inactive"
    superseded = "superseded"
    archived = "archived"


class ActionClassification(enum.StrEnum):
    safe = "safe"
    restricted = "restricted"
    privileged = "privileged"
    forbidden = "forbidden"


class RiskTier(enum.StrEnum):
    standard = "standard"
    elevated = "elevated"
    high = "high"
    critical = "critical"


class ApprovalRoutingStrategy(enum.StrEnum):
    direct = "direct"
    escalation_chain = "escalation_chain"
    quorum = "quorum"
    any_of = "any_of"


class GovernanceEventType(enum.StrEnum):
    policy_evaluated = "policy_evaluated"
    approval_routed = "approval_routed"
    escalation_triggered = "escalation_triggered"
    escalation_resolved = "escalation_resolved"
    quorum_vote_cast = "quorum_vote_cast"
    quorum_met = "quorum_met"
    override_applied = "override_applied"
    freeze_activated = "freeze_activated"
    freeze_deactivated = "freeze_deactivated"
    kill_switch_triggered = "kill_switch_triggered"
    policy_superseded = "policy_superseded"
    policy_snapshot_captured = "policy_snapshot_captured"
    delegation_granted = "delegation_granted"
    delegation_revoked = "delegation_revoked"
    action_denied = "action_denied"
    freeze_propagated = "freeze_propagated"
    invariant_violated = "invariant_violated"


class DelegationStatus(enum.StrEnum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class SophiaSessionStatus(enum.StrEnum):
    initializing = "initializing"
    active = "active"
    interrupted = "interrupted"
    awaiting_handoff = "awaiting_handoff"
    handed_off = "handed_off"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class SophiaTurnStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    interrupted = "interrupted"
    cancelled = "cancelled"
    failed = "failed"


class SophiaInterruptionReason(enum.StrEnum):
    user_barge_in = "user_barge_in"
    timeout = "timeout"
    governance_block = "governance_block"
    tool_approval_required = "tool_approval_required"
    handoff_requested = "handoff_requested"
    cancellation = "cancellation"
    error = "error"


class SophiaHandoffStatus(enum.StrEnum):
    requested = "requested"
    accepted = "accepted"
    completed = "completed"
    rejected = "rejected"
    timed_out = "timed_out"


class SophiaChannelType(enum.StrEnum):
    text = "text"
    voice = "voice"
    phone = "phone"


class SophiaEventType(enum.StrEnum):
    session_started = "session_started"
    session_completed = "session_completed"
    session_cancelled = "session_cancelled"
    session_failed = "session_failed"
    turn_started = "turn_started"
    turn_completed = "turn_completed"
    turn_interrupted = "turn_interrupted"
    turn_cancelled = "turn_cancelled"
    tool_permitted = "tool_permitted"
    tool_blocked = "tool_blocked"
    governance_evaluated = "governance_evaluated"
    handoff_requested = "handoff_requested"
    handoff_accepted = "handoff_accepted"
    handoff_completed = "handoff_completed"
    checkpoint_saved = "checkpoint_saved"
    context_assembled = "context_assembled"
    cancellation_requested = "cancellation_requested"
    recovery_initiated = "recovery_initiated"
    mode_changed = "mode_changed"


class ResearchJobStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ResearchTaskStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    skipped = "skipped"
    blocked = "blocked"


class ResearchEvidenceStatus(enum.StrEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    duplicate = "duplicate"


class ResearchMemoryScope(enum.StrEnum):
    job = "job"
    task = "task"
    session = "session"


class ContextBudgetLevel(enum.StrEnum):
    platform = "platform"
    phase = "phase"
    graph = "graph"
    agent = "agent"
    call = "call"


class ResearchPlanStatus(enum.StrEnum):
    draft = "draft"
    active = "active"
    revised = "revised"
    completed = "completed"
    abandoned = "abandoned"


class ResearchEventType(enum.StrEnum):
    job_created = "job_created"
    job_started = "job_started"
    job_paused = "job_paused"
    job_resumed = "job_resumed"
    job_completed = "job_completed"
    job_failed = "job_failed"
    job_cancelled = "job_cancelled"
    job_checkpointed = "job_checkpointed"
    task_created = "task_created"
    task_started = "task_started"
    task_completed = "task_completed"
    task_failed = "task_failed"
    task_cancelled = "task_cancelled"
    task_skipped = "task_skipped"
    task_retried = "task_retried"
    evidence_recorded = "evidence_recorded"
    evidence_accepted = "evidence_accepted"
    evidence_rejected = "evidence_rejected"
    evidence_deduplicated = "evidence_deduplicated"
    memory_written = "memory_written"
    memory_expired = "memory_expired"
    memory_cleared = "memory_cleared"
    plan_created = "plan_created"
    plan_revised = "plan_revised"
    plan_completed = "plan_completed"
    plan_abandoned = "plan_abandoned"
    governance_checked = "governance_checked"
    budget_warning = "budget_warning"
    budget_exceeded = "budget_exceeded"
    depth_limit_reached = "depth_limit_reached"
    timeout_triggered = "timeout_triggered"
    dead_letter = "dead_letter"
    replay_started = "replay_started"
    replay_completed = "replay_completed"


class SophiaSessionMode(enum.StrEnum):
    ai = "ai"
    human_takeover = "human_takeover"