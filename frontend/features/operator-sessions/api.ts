import env from '@/config/environment'

const BASE = `${env.apiUrl}/api/v1/operator-sessions`

// ── Types ────────────────────────────────────────────────────────────────────

export interface RealtimeSessionResponse {
  id: string
  user_id: string
  socket_id: string
  session_status: 'connected' | 'disconnected' | 'expired'
  connected_at: string
  disconnected_at: string | null
  last_heartbeat_at: string | null
  device_info: string | null
}

export interface StaleCleanupResponse {
  expired_count: number
  session_ids: string[]
}

export interface SessionPage {
  items: RealtimeSessionResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface SessionCountResponse {
  count: number
}

// ── Client ───────────────────────────────────────────────────────────────────

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

export const operatorSessionsApi = {
  list: (page = 1, pageSize = 20) =>
    request<SessionPage>(`?page=${page}&page_size=${pageSize}`),

  count: () => request<SessionCountResponse>('/count'),

  disconnect: (sessionId: string) =>
    request<RealtimeSessionResponse>(`/${sessionId}/disconnect`, { method: 'POST' }),

  cleanupStale: (thresholdSeconds?: number) => {
    const qs = thresholdSeconds != null ? `?threshold_seconds=${thresholdSeconds}` : ''
    return request<StaleCleanupResponse>(`/cleanup/stale${qs}`, { method: 'POST' })
  },
}
