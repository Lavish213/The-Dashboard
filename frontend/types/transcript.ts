export type TranscriptStatus =
  | 'created'
  | 'active'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'archived'

export type TranscriptSourceType = 'call' | 'upload' | 'realtime' | 'manual'
export type TranscriptStreamType = 'agent' | 'user' | 'system' | 'mixed'

export interface Transcript {
  id: string
  workflow_id: string | null
  call_id: string | null
  lead_id: string | null
  transcript_status: TranscriptStatus
  source_type: TranscriptSourceType
  duration_seconds: number | null
  created_at: string
  updated_at: string
}

export interface TranscriptChunk {
  id: string
  transcript_id: string
  chunk_index: number
  speaker: string
  text: string
  stream_type: TranscriptStreamType
  created_at: string
}

export interface TranscriptEvent {
  id: string
  transcript_id: string
  event_type: string
  sequence: number
  payload: Record<string, unknown>
  created_at: string
}

export interface TranscriptReplay {
  transcript_id: string
  replayed_events: number
  final_status: TranscriptStatus
  chunk_count: number
}

export interface ChunksPage {
  items: TranscriptChunk[]
  total: number
  page: number
  page_size: number
}
