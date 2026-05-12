// Mirrors backend WorkflowStatus enum
export type WorkflowStatus =
  | 'pending'
  | 'active'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'

// Mirrors backend WorkflowType enum
export type WorkflowType =
  | 'outreach'
  | 'qualification'
  | 'follow_up'
  | 'closing'

// Mirrors backend WorkflowResponse schema
export interface Workflow {
  id: string
  workflow_type: WorkflowType
  workflow_status: WorkflowStatus
  current_step: string | null
  correlation_id: string
  lead_id: string | null
  initiated_by: string | null
  expires_at: string | null
  created_at: string
  updated_at: string
}

// Mirrors backend WorkflowEvent shape returned from GET /workflows/:id/events
export interface WorkflowEvent {
  id: string
  event_type: string
  payload: Record<string, unknown>
  actor_type: 'user' | 'system' | 'ai'
  actor_id: string | null
  correlation_id: string
  causation_id: string | null
  created_at: string
}

// Mirrors replay response
export interface WorkflowReplay {
  workflow_id: string
  replayed_events: number
  final_status: WorkflowStatus
  final_step: string | null
}
