'use client'

import { useQuery } from '@tanstack/react-query'
import { useQueryState, parseAsInteger, parseAsString } from 'nuqs'
import { PageContainer } from '@/components/workspace/PageContainer'
import { SkeletonFeed } from '@/components/ui/skeleton-states'
import { apiFetch } from '@/services/api'

interface ActivityEvent {
  id: string
  event_type: string
  payload: Record<string, unknown>
  occurred_at: string
}

const EVENT_FILTERS = [
  { value: '', label: 'All' },
  { value: 'sophia', label: 'Sophia' },
  { value: 'lead', label: 'Leads' },
  { value: 'workflow', label: 'Workflows' },
  { value: 'approval', label: 'Approvals' },
]

export default function ActivityPage() {
  const [page, setPage] = useQueryState('page', parseAsInteger.withDefault(1))
  const [eventType, setEventType] = useQueryState('type', parseAsString.withDefault(''))

  const { data, isPending: loading, error } = useQuery({
    queryKey: ['activity', page, eventType],
    queryFn: ({ signal }) => {
    const params = new URLSearchParams({ page: String(page), page_size: '50' })
    if (eventType) params.set('event_type', eventType)
    return apiFetch<{ items: ActivityEvent[]; total: number; total_pages: number }>(`/api/v1/activity?${params}`, { signal })
    },
  })
  const events = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  return (
    <PageContainer title="Activity" description={`${total} domain events`}>
      {error && <p role="alert" className="text-sm text-destructive">Activity could not be loaded.</p>}
      <div className="flex gap-1.5 mb-4 flex-wrap">
        {EVENT_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => { setEventType(f.value); setPage(1) }}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              eventType === f.value
                ? 'border-teal-500/30 bg-teal-500/10 text-teal-400'
                : 'border-border text-muted-foreground hover:text-foreground'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <SkeletonFeed rows={8} />
      ) : (
        <div className="space-y-2">
          {!error && events.length === 0 && (
            <div className="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
              No activity yet
            </div>
          )}
          {events.map((event) => (
            <div key={event.id} className="flex items-start gap-3 rounded-lg border bg-card px-4 py-3 hover:bg-muted/30 transition-colors">
              <div className="h-2 w-2 rounded-full bg-teal-400 flex-shrink-0 mt-1.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-mono font-medium text-foreground truncate">{event.event_type}</span>
                  <span className="text-xs text-muted-foreground flex-shrink-0 tabular-nums">
                    {new Date(event.occurred_at).toLocaleString()}
                  </span>
                </div>
                {Object.keys(event.payload).length > 0 && (
                  <p className="text-xs text-muted-foreground mt-0.5 truncate">{JSON.stringify(event.payload)}</p>
                )}
              </div>
            </div>
          ))}
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
