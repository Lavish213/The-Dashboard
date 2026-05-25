'use client'

import { useEffect, useState } from 'react'
import { useQueryState, parseAsInteger, parseAsString } from 'nuqs'
import { PageContainer } from '@/components/workspace/PageContainer'
import { SkeletonTable } from '@/components/ui/skeleton-states'
import { apiFetch } from '@/services/api'

type CallStatus = 'initiated' | 'ringing' | 'connected' | 'completed' | 'failed' | 'no_answer' | 'voicemail'

interface Call {
  id: string
  lead_id: string | null
  call_status: CallStatus
  provider: string
  duration_seconds: number | null
  started_at: string | null
  created_at: string
}

const STATUS_COLORS: Record<CallStatus, string> = {
  initiated: 'bg-muted text-muted-foreground border-border',
  ringing: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  connected: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  completed: 'bg-green-500/10 text-green-400 border-green-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  no_answer: 'bg-muted text-muted-foreground border-border',
  voicemail: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

const STATUSES = [
  { value: '', label: 'All' },
  { value: 'completed', label: 'Completed' },
  { value: 'connected', label: 'Connected' },
  { value: 'no_answer', label: 'No answer' },
  { value: 'voicemail', label: 'Voicemail' },
  { value: 'failed', label: 'Failed' },
]

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function CallsPage() {
  const [calls, setCalls] = useState<Call[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [page, setPage] = useQueryState('page', parseAsInteger.withDefault(1))
  const [callStatus, setCallStatus] = useQueryState('status', parseAsString.withDefault(''))

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page), page_size: '50' })
    if (callStatus) params.set('call_status', callStatus)
    apiFetch<{ items: Call[]; total: number; total_pages: number }>(`/api/v1/calls?${params}`)
      .then((r) => { setCalls(r.items ?? []); setTotal(r.total ?? 0); setTotalPages(r.total_pages ?? 1) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [page, callStatus])

  return (
    <PageContainer title="Calls" description={`${total} total calls`}>
      <div className="flex gap-1.5 mb-4 flex-wrap">
        {STATUSES.map((s) => (
          <button
            key={s.value}
            onClick={() => { setCallStatus(s.value); setPage(1) }}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              callStatus === s.value
                ? 'border-teal-500/30 bg-teal-500/10 text-teal-400'
                : 'border-border text-muted-foreground hover:text-foreground'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {loading ? (
        <SkeletonTable rows={8} cols={5} />
      ) : (
        <div className="rounded-lg border bg-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Provider</th>
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Duration</th>
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Started</th>
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Lead</th>
              </tr>
            </thead>
            <tbody>
              {calls.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-12 text-center text-sm text-muted-foreground">No calls found</td></tr>
              )}
              {calls.map((call) => (
                <tr key={call.id} className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[call.call_status]}`}>
                      {call.call_status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{call.provider}</td>
                  <td className="px-4 py-3 text-sm tabular-nums text-foreground">{formatDuration(call.duration_seconds)}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {call.started_at ? new Date(call.started_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-muted-foreground">
                    {call.lead_id ? call.lead_id.slice(0, 8) + '…' : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-4">
          <button disabled={page === 1} onClick={() => setPage(page - 1)} className="rounded border px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-muted transition-colors">Previous</button>
          <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
          <button disabled={page === totalPages} onClick={() => setPage(page + 1)} className="rounded border px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-muted transition-colors">Next</button>
        </div>
      )}
    </PageContainer>
  )
}