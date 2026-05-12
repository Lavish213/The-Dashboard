import env from '@/config/environment'

const API = env.apiUrl

// ── Types ────────────────────────────────────────────────────────────────────

export interface HealthStatus {
  status: string
  env: string
  version: string
}

export interface ReadinessStatus {
  status: string
  db: string
}

export interface MetricsSnapshot {
  uptime_seconds: number
  requests: Record<string, unknown>
  websocket: Record<string, unknown>
  operator_sessions: Record<string, unknown>
  notifications: Record<string, unknown>
  audit: Record<string, unknown>
  call_sessions: Record<string, unknown>
}

// ── Client ───────────────────────────────────────────────────────────────────

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

export const healthApi = {
  health: () => request<HealthStatus>('/api/health'),
  ready: () => request<ReadinessStatus>('/api/ready'),
  metrics: () => request<MetricsSnapshot>('/api/metrics'),
}
