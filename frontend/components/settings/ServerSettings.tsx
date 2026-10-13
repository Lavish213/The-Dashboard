'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { useAuthStore } from '@/stores/auth.store'
import { Button } from '@/components/ui/button'

export interface ServerConfiguration {
  source: 'dashboard_server'
  app_version: string
  environment: string
  security: { access_token_minutes: number; refresh_token_days: number }
  permissions: string[]
  notifications: { channel: string; delivery: string }
  voice_configuration: { available: boolean; reason: string }
  calendar_booking: { available: boolean; reason: string }
}

export function useServerConfiguration() {
  return useQuery({ queryKey: ['server-configuration'], queryFn: ({ signal }) => apiFetch<ServerConfiguration>('/api/v1/settings', { signal }) })
}

interface Page<T> { items: T[]; total: number; total_pages: number }
interface Notification { id: string; title: string; body: string; read_at: string | null; created_at: string }
interface TeamMember { id: string; full_name: string | null; email: string; role: string; status: string }

export function NotificationFeed() {
  const [page, setPage] = useState(1)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const client = useQueryClient()
  const feed = useQuery({ queryKey: ['notifications', 'feed', page, unreadOnly], queryFn: ({ signal }) => apiFetch<Page<Notification>>(`/api/v1/notifications?page=${page}&unread_only=${unreadOnly}`, { signal }) })
  const unread = useQuery({ queryKey: ['notifications', 'unread'], queryFn: ({ signal }) => apiFetch<{ unread_count: number }>('/api/v1/notifications/unread-count', { signal }) })
  const read = useMutation({
    mutationFn: (id: string | null) => apiFetch(id ? `/api/v1/notifications/${id}/read` : '/api/v1/notifications/read-all', { method: 'POST' }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['notifications'] }),
  })

  return <div className="space-y-4">
    <h2 className="text-lg font-semibold">Your notifications</h2>
    <p className="text-sm text-muted-foreground">In-app notifications from this dashboard. Email, SMS and escalation policies are managed separately.</p>
    <div className="flex flex-wrap items-center gap-3">
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={unreadOnly} onChange={e => { setUnreadOnly(e.target.checked); setPage(1) }} />Unread only</label>
      <span className="text-sm text-muted-foreground">{unread.data ? `${unread.data.unread_count} unread` : 'Unread count unavailable'}</span>
      <Button size="sm" variant="outline" disabled={read.isPending || !unread.data?.unread_count} onClick={() => read.mutate(null)}>Mark all read</Button>
    </div>
    {(feed.isError || unread.isError) && <p role="alert" className="text-sm text-destructive">Notifications could not be refreshed. Existing records may be stale.</p>}
    {read.isError && <p role="alert" className="text-sm text-destructive">Read status was not saved. Try again.</p>}
    {feed.isPending && <p role="status" className="text-sm text-muted-foreground">Loading notifications…</p>}
    {feed.data && !feed.isError && feed.data.items.length === 0 && <p className="text-sm text-muted-foreground">No matching notifications.</p>}
    {feed.data?.items.map(item => <article key={item.id} className="space-y-2 rounded-md border p-3">
      <h3 className="text-sm font-semibold">{item.title}</h3>
      <p className="break-words text-sm text-muted-foreground">{item.body}</p>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <time dateTime={item.created_at} className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</time>
        {item.read_at ? <span className="text-xs text-muted-foreground">Read</span> : <Button size="sm" variant="outline" disabled={read.isPending} onClick={() => read.mutate(item.id)}>Mark read</Button>}
      </div>
    </article>)}
    <div className="flex items-center gap-3">
      <Button size="sm" variant="outline" disabled={page === 1 || feed.isFetching} onClick={() => setPage(p => p - 1)}>Previous notifications</Button>
      <span className="text-xs text-muted-foreground">Page {page}{feed.data ? ` of ${feed.data.total_pages}` : ''}</span>
      <Button size="sm" variant="outline" disabled={!feed.data || page >= feed.data.total_pages || feed.isFetching} onClick={() => setPage(p => p + 1)}>Next notifications</Button>
    </div>
  </div>
}

export function TeamRoster() {
  const role = useAuthStore(s => s.user?.role)
  const [page, setPage] = useState(1)
  const query = useQuery({ queryKey: ['team', page], queryFn: ({ signal }) => apiFetch<Page<TeamMember>>(`/api/v1/settings/team?page=${page}`, { signal }), enabled: role === 'admin' })
  if (role !== 'admin') return <p className="text-sm text-muted-foreground">The team roster is available to administrators.</p>
  return <section className="space-y-3" aria-labelledby="team-heading">
    <h2 id="team-heading" className="text-lg font-semibold">Team roster</h2>
    <p className="text-sm text-muted-foreground">Read-only records from the server. Account creation and role changes are not exposed here.</p>
    {query.isPending && <p role="status" className="text-sm text-muted-foreground">Loading team…</p>}
    {query.isError && <p role="alert" className="text-sm text-destructive">Team roster unavailable.</p>}
    {query.data?.items.map(member => <div key={member.id} className="rounded-md border p-3 text-sm">
      <p className="font-medium">{member.full_name ?? member.email}</p>
      <p className="break-words text-muted-foreground">{member.email} · {member.role} · {member.status}</p>
    </div>)}
    {query.data && !query.isError && query.data.items.length === 0 && <p className="text-sm text-muted-foreground">No team members.</p>}
    <div className="flex items-center gap-3">
      <Button size="sm" variant="outline" disabled={page === 1 || query.isFetching} onClick={() => setPage(p => p - 1)}>Previous team page</Button>
      <span className="text-xs text-muted-foreground">Page {page}</span>
      <Button size="sm" variant="outline" disabled={!query.data || page >= query.data.total_pages || query.isFetching} onClick={() => setPage(p => p + 1)}>Next team page</Button>
    </div>
  </section>
}
