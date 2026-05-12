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
