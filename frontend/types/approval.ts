// Mirrors backend ApprovalType enum
export type ApprovalType =
  | 'offer'
  | 'price_reduction'
  | 'skip_trace'
  | 'outreach'

// Mirrors backend ApprovalStatus enum
export type ApprovalStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'expired'
  | 'escalated'

// Mirrors backend RiskLevel enum
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

// Mirrors backend ApprovalResponse schema
export interface Approval {
  id: string
  workflow_id: string
  approval_type: ApprovalType
  approval_status: ApprovalStatus
  requested_by: string | null
  resolved_by: string | null
  expires_at: string | null
  risk_level: RiskLevel
  resolution_notes: string | null
  created_at: string
  updated_at: string
}

export interface ApprovalPage {
  items: Approval[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApprovalCreateBody {
  workflow_id: string
  approval_type: ApprovalType
  requested_by?: string | null
  risk_level?: RiskLevel
  expires_at?: string | null
}

export interface ApprovalResolveBody {
  approval_status: 'approved' | 'rejected'
  resolved_by: string
  resolution_notes?: string | null
}
