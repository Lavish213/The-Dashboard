import env from '@/config/environment'

const BASE = `${env.apiUrl}/api/v1/audit`

// ── Types ────────────────────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: string
  actor_id: string | null
  actor_type: 'user' | 'system' | 'ai'
  action: string
  target_type: string
  target_id: string | null
  correlation_id: string | null
  payload: Record<string, unknown>
  created_at: string
}

export interface AuditPage {
  items: AuditLogEntry[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AuditFilters {
  actor_id?: string
  target_type?: string
  target_id?: string
  action?: string
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

export const auditApi = {
  list: (filters: AuditFilters, page = 1, pageSize = 20) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (filters.actor_id) params.set('actor_id', filters.actor_id)
    if (filters.target_type) params.set('target_type', filters.target_type)
    if (filters.target_id) params.set('target_id', filters.target_id)
    if (filters.action) params.set('action', filters.action)
    return request<AuditPage>(`?${params.toString()}`)
  },

  correlation: (correlationId: string, page = 1, pageSize = 20) =>
    request<AuditPage>(
      `/correlation/${encodeURIComponent(correlationId)}?page=${page}&page_size=${pageSize}`
    ),
}
