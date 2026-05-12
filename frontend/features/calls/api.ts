import env from '@/config/environment'
import type {
  CallEvent,
  CallEventPage,
  CallParticipant,
  CallSession,
  ConnectionState,
  JoinSessionBody,
} from '@/types/call'

const BASE = `${env.apiUrl}/api/v1/calls`

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

export const callsApi = {
  create: (callId?: string) =>
    request<CallSession>('', {
      method: 'POST',
      body: JSON.stringify({ call_id: callId ?? null }),
    }),

  get: (sessionId: string) =>
    request<CallSession>(`/${sessionId}`),

  complete: (sessionId: string) =>
    request<CallSession>(`/${sessionId}/complete`, { method: 'POST' }),

  fail: (sessionId: string, reason = '') =>
    request<CallSession>(`/${sessionId}/fail?reason=${encodeURIComponent(reason)}`, {
      method: 'POST',
    }),

  join: (sessionId: string, body: JoinSessionBody) =>
    request<CallParticipant>(`/${sessionId}/join`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  leave: (sessionId: string, participantId: string) =>
    request<CallParticipant>(`/${sessionId}/participants/${participantId}/leave`, {
      method: 'POST',
    }),

  heartbeat: (sessionId: string, participantId: string) =>
    fetch(`${BASE}/${sessionId}/participants/${participantId}/heartbeat`, {
      method: 'POST',
    }),

  participants: (sessionId: string) =>
    request<CallParticipant[]>(`/${sessionId}/participants`),

  events: (sessionId: string, page = 1, pageSize = 100) =>
    request<CallEventPage>(
      `/${sessionId}/events?page=${page}&page_size=${pageSize}`
    ),

  replay: (sessionId: string) =>
    request<{ session_id: string; replayed_events: number; final_status: string; participant_count: number }>(
      `/${sessionId}/replay`
    ),

  presence: (sessionId: string) =>
    request<ConnectionState[]>(`/${sessionId}/presence`),
}
