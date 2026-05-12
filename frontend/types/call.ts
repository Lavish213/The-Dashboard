// Mirrors backend CallSessionStatus enum
export type CallSessionStatus = 'waiting' | 'active' | 'completed' | 'failed'

// Mirrors backend ParticipantRole enum
export type ParticipantRole = 'operator' | 'lead' | 'observer'

// Mirrors backend ParticipantStatus enum
export type ParticipantStatus = 'joined' | 'left' | 'reconnecting' | 'dropped'

// Mirrors backend CallSessionResponse schema
export interface CallSession {
  id: string
  call_id: string | null
  session_status: CallSessionStatus
  correlation_id: string
  started_at: string | null
  ended_at: string | null
  created_at: string
  updated_at: string
}

// Mirrors backend CallParticipantResponse schema
export interface CallParticipant {
  id: string
  session_id: string
  user_id: string | null
  role: ParticipantRole
  participant_status: ParticipantStatus
  connection_id: string | null
  joined_at: string
  left_at: string | null
  last_heartbeat_at: string | null
  created_at: string
  updated_at: string
}

// Mirrors backend CallEventResponse schema
export interface CallEvent {
  id: string
  session_id: string
  event_type: string
  sequence: number
  payload: Record<string, unknown>
  created_at: string
}

// Mirrors backend ConnectionStateResponse schema
export interface ConnectionState {
  participant_id: string
  session_id: string
  participant_status: ParticipantStatus
  connection_id: string | null
  last_heartbeat_at: string | null
  is_stale: boolean
}

export interface CallEventPage {
  items: CallEvent[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface JoinSessionBody {
  user_id?: string | null
  role: ParticipantRole
  connection_id?: string | null
}
