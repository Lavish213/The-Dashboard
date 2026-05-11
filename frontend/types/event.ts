/**
 * Domain event payload types for RealtimeEvent.payload discrimination.
 */
import type { RealtimeEvent } from "./websocket";

// ── Approval events ───────────────────────────────────────────────────────────

export interface ApprovalCreatedPayload {
  approval_id: string;
  workflow_id: string;
  requested_by: string;
}

export interface ApprovalDecidedPayload {
  approval_id: string;
  decision: "approved" | "rejected";
  decided_by: string;
}

// ── Workflow events ───────────────────────────────────────────────────────────

export interface WorkflowStatusChangedPayload {
  workflow_id: string;
  old_status: string;
  new_status: string;
}

// ── Lead events ───────────────────────────────────────────────────────────────

export interface LeadAssignedPayload {
  lead_id: string;
  assigned_to: string;
}

// ── Typed event discriminated union ──────────────────────────────────────────

export type TypedRealtimeEvent =
  | (RealtimeEvent & { event_type: "approval.created"; payload: ApprovalCreatedPayload })
  | (RealtimeEvent & { event_type: "approval.decided"; payload: ApprovalDecidedPayload })
  | (RealtimeEvent & { event_type: "workflow.status_changed"; payload: WorkflowStatusChangedPayload })
  | (RealtimeEvent & { event_type: "lead.assigned"; payload: LeadAssignedPayload })
  | RealtimeEvent; // fallback for unknown event types
