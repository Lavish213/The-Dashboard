'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'

interface DeliveryOverview {
  inventory: { accepted: number; uncertain_submission: number; pending_projection: number } | null
  journal: { pending: number; received: number; oldest_pending_seconds: number }
  messages: Array<{ intent_id: string; lead_id: string | null; channel: string; delivery_status: string; opened: boolean; clicked: boolean; suppressed: boolean }>
}

export function DeliveryEvidence() {
  const query = useQuery({ queryKey: ['provider-delivery'], queryFn: ({ signal }) => apiFetch<DeliveryOverview>('/api/v1/source-review/delivery', { signal }), refetchInterval: 15000, retry: false })
  return <section aria-label="Message delivery receipts" className="mb-6 rounded-lg border bg-card p-4 space-y-3">
    <h2 className="font-semibold">Message delivery receipts</h2>
    <p className="text-sm">Latest 100 projected messages, including provider-accepted sends awaiting callbacks. Opens and clicks can be automated; they do not prove a person read or accepted an offer. Missing callbacks leave delivery unconfirmed.</p>
    {query.isPending && <p role="status">Loading delivery receipts…</p>}
    {query.isError && <p role="alert">Delivery evidence unavailable. Previous results may be stale.</p>}
    {query.data && <>
      {query.data.inventory ? <><p className="text-sm">Journaled SMS/email accepted: {query.data.inventory.accepted} · Submission outcome uncertain: {query.data.inventory.uncertain_submission} · Awaiting inventory staging: {query.data.inventory.pending_projection}</p>{query.data.inventory.uncertain_submission > 0 && <p role="status">Uncertain submissions require provider reconciliation before any resend.</p>}{query.data.inventory.pending_projection > 0 && <p role="status">Accepted-message inventory is still staging; the list may be incomplete.</p>}</> : <p role="status">Accepted-message inventory unavailable from this source version.</p>}
      <p className="text-xs text-muted-foreground">Inventory covers journaled SMS/email. Calls and unjournaled historical sends require separate reconciliation.</p>
      <p className="text-sm">{query.isError ? 'Last reported' : 'Recorded'} events: {query.data.journal.received} · Awaiting database sync: {query.data.journal.pending} · Oldest pending: {query.data.journal.oldest_pending_seconds}s</p>
      {query.data.journal.pending > 0 && <p role="status">Some received events are awaiting recovery. The message list may be incomplete.</p>}
      {query.data.messages.length === 0 && <p>No synced message receipts available.</p>}
      <ul className="space-y-2 text-sm">{query.data.messages.map(message => <li key={message.intent_id} className="rounded border p-3 break-all">
        <p>{message.channel.toUpperCase()} · {message.delivery_status.replaceAll('_', ' ')}</p>
        <p className="text-xs text-muted-foreground">Message {message.intent_id.slice(0, 12)} · Lead {message.lead_id ?? 'unlinked'}</p>
        {message.delivery_status === 'conflicting_receipts' && <p>Conflicting provider receipts require review.</p>}
        <p>Open event: {message.opened ? 'yes' : 'no'} · Click event: {message.clicked ? 'yes' : 'no'} · Address suppressed: {message.suppressed ? 'yes' : 'no'}</p>
      </li>)}</ul>
    </>}
    <Button variant="outline" disabled={query.isFetching} onClick={() => void query.refetch()}>Refresh delivery receipts</Button>
  </section>
}
