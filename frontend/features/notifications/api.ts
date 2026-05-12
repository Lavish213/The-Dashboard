import env from '@/config/environment'

const BASE = `${env.apiUrl}/api/v1/notifications`

// ── Types ────────────────────────────────────────────────────────────────────

export interface NotificationItem {
  id: string
  user_id: string
  notification_type: 'approval_required' | 'workflow_update' | 'system_alert' | 'lead_activity'
  title: string
  body: string
  read_at: string | null
  created_at: string
}

export interface NotificationPage {
  items: NotificationItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface UnreadCountResponse {
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

export const notificationsApi = {
  list: (userId: string, page = 1, pageSize = 20, unreadOnly = false) => {
    const params = new URLSearchParams({
      user_id: userId,
      page: String(page),
      page_size: String(pageSize),
      unread_only: String(unreadOnly),
    })
    return request<NotificationPage>(`?${params.toString()}`)
  },

  markRead: (id: string, userId: string) =>
    request<NotificationItem>(`/${id}/read?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
    }),

  markAllRead: (userId: string) =>
    request<{ marked_count: number }>(
      `/read-all?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' }
    ),

  unreadCount: (userId: string) =>
    request<UnreadCountResponse>(`/unread-count?user_id=${encodeURIComponent(userId)}`),
}
