import env from '@/config/environment'
import type {
  Transcript,
  TranscriptChunk,
  TranscriptEvent,
  TranscriptReplay,
  TranscriptSourceType,
  TranscriptStreamType,
} from '@/types/transcript'

const BASE = `${env.apiUrl}/api/v1/transcripts`

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

export interface CreateTranscriptBody {
  source_type?: TranscriptSourceType
  workflow_id?: string | null
  call_id?: string | null
  lead_id?: string | null
}

export interface AppendChunkBody {
  speaker: string
  text: string
  stream_type?: TranscriptStreamType
  chunk_index?: number | null
}

export const transcriptsApi = {
  create: (body: CreateTranscriptBody) =>
    request<Transcript>('', { method: 'POST', body: JSON.stringify(body) }),

  get: (id: string) => request<Transcript>(`/${id}`),

  start: (id: string) =>
    request<Transcript>(`/${id}/start`, { method: 'POST' }),

  pause: (id: string) =>
    request<Transcript>(`/${id}/pause`, { method: 'POST' }),

  resume: (id: string) =>
    request<Transcript>(`/${id}/resume`, { method: 'POST' }),

  complete: (id: string) =>
    request<Transcript>(`/${id}/complete`, { method: 'POST' }),

  fail: (id: string, reason = '') =>
    request<Transcript>(`/${id}/fail?reason=${encodeURIComponent(reason)}`, { method: 'POST' }),

  archive: (id: string) =>
    request<Transcript>(`/${id}/archive`, { method: 'POST' }),

  appendChunk: (id: string, body: AppendChunkBody) =>
    request<TranscriptChunk>(`/${id}/chunks`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  chunks: (id: string, page = 1, pageSize = 50) =>
    request<TranscriptChunk[]>(`/${id}/chunks?page=${page}&page_size=${pageSize}`),

  events: (id: string, page = 1, pageSize = 100) =>
    request<TranscriptEvent[]>(`/${id}/events?page=${page}&page_size=${pageSize}`),

  replay: (id: string) => request<TranscriptReplay>(`/${id}/replay`),
}
