'use client'

import Link from 'next/link'
import { useInfiniteQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'

interface SourceRecord {
  id: string
  lead_id: string
  full_name: string
  kind: string
  state: string
  at: string | null
  amount_cents: number | null
  text: string | null
  evidence_status: string
}
interface SourcePage { items: SourceRecord[]; page: number; total_pages: number }

export function SourceOperations({ view, start, end }: { view: 'calendar' | 'deals' | 'followups'; start?: string; end?: string }) {
  const query = useInfiniteQuery({
    queryKey: ['source-operations', view, start, end], initialPageParam: 1,
    queryFn: ({ pageParam, signal }) => {
      const params = new URLSearchParams({ view, page: String(pageParam) })
      if (start) params.set('start', start)
      if (end) params.set('end', end)
      return apiFetch<SourcePage>(`/api/v1/leads/source-operations?${params}`, { signal })
    },
    getNextPageParam: page => page.page < page.total_pages ? page.page + 1 : undefined,
  })
  const records = query.data?.pages.flatMap(page => page.items) ?? []
  return <section aria-label="Sophia saved operations" className="mb-6 rounded-lg border bg-card p-4 space-y-3">
    <h2 className="font-semibold">Sophia saved {view === 'deals' ? 'offers' : view === 'calendar' ? 'walkthroughs and callbacks' : 'follow-ups and email replies'}</h2>
    {query.isPending && <p role="status">Loading saved source records…</p>}
    {query.error && <div role="alert"><p>Source records unavailable. Previously loaded records may be stale.</p><Button variant="outline" onClick={() => void query.refetch()}>Retry source records</Button></div>}
    {!query.isPending && !query.error && records.length === 0 && <p className="text-sm text-muted-foreground">No source records in the loaded page.</p>}
    <ul className="space-y-2">{records.map(record => <li key={record.id} className="border-t pt-2 text-sm">
      <Link href={`/leads/${encodeURIComponent(record.lead_id)}`} className="font-medium underline">{record.full_name}</Link>
      <p>{record.kind.replaceAll('_', ' ')} · {record.state.replaceAll('_', ' ')}{record.at ? ` · ${new Date(record.at).toLocaleString('en-US', { timeZone: 'America/Los_Angeles' })} PT` : ''}</p>
      {record.amount_cents != null && <p>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(record.amount_cents / 100)}</p>}
      {record.text && <p className="whitespace-pre-wrap break-words">{record.text}</p>}
      {record.evidence_status !== 'current' && <p className="text-amber-700 dark:text-amber-400">Source record is stale; refresh and confirm before acting.</p>}
    </li>)}</ul>
    {query.hasNextPage && <Button variant="outline" disabled={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()}>{query.isFetchingNextPage ? 'Loading…' : 'Load more source records'}</Button>}
  </section>
}
