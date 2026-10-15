'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth.store'

interface Hold { lead_id: string; email: string | null; count: number; stopped: boolean; pending: number; text: string; fingerprint: string; can_resume: boolean; review_state: string | null; error: string | null }

function HoldCard({hold, refresh, available}: {hold: Hold; refresh: () => void; available: boolean}) {
  const user = useAuthStore(state => state.user)
  const [reason, setReason] = useState('')
  const [requestId, setRequestId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const mayResume = user && ['admin','operator'].includes(user.role) && hold.can_resume && !hold.stopped && hold.pending === 0 && hold.review_state !== 'pending'
  async function resume() {
    if (!mayResume || !available || busy || reason.trim().length < 10) return
    const identity = requestId ?? crypto.randomUUID()
    setRequestId(identity)
    setBusy(true)
    try {
      const receipt = await apiFetch<{persisted: boolean; request_id: string; lead_id: string; state: string}>(`/api/v1/source-review/email-holds/${hold.lead_id}/resume`, {method: 'POST', body: JSON.stringify({request_id: identity, fingerprint: hold.fingerprint, reason: reason.trim()})})
      if (!receipt.persisted || receipt.request_id !== identity || receipt.lead_id !== hold.lead_id) throw new Error('Unconfirmed resumption receipt')
      setMessage(receipt.state === 'applied' ? 'Source and local journal confirmed resumption of this email sequence.' : receipt.state === 'pending' ? 'Reviewed resumption queued. Email follow-ups remain held until both source and local journal confirm it.' : 'New evidence or a recovery limit requires another review. Email follow-ups remain held.')
      refresh()
    } catch { setMessage('Resumption could not be confirmed. Refresh this review to check the saved state.') }
    finally { setBusy(false) }
  }
  return <article className="rounded border p-4 space-y-2">
    <h3 className="font-medium break-all">{hold.email ?? 'Email identity unverified'}</h3>
    <p className="text-sm break-all">Source lead {hold.lead_id} · {hold.count} recorded replies</p>
    <p className="whitespace-pre-wrap text-sm">{hold.text}</p>
    {hold.stopped ? <p role="alert">STOP or opt-out: resumption is blocked.</p> : hold.pending ? <p role="status">Reply persistence is pending. Review becomes available after recovery.</p> : <p className="text-sm">Email follow-ups are paused for operator review.</p>}
    {hold.review_state && <p className="text-sm">Resumption review: {hold.review_state}{hold.error ? ` · ${hold.error}` : ''}</p>}
    {mayResume && <><label className="block text-sm">Email resumption review reason<textarea value={reason} maxLength={1000} onChange={event => {setReason(event.target.value); setRequestId(null)}} className="block w-full rounded border bg-background p-2" /></label><Button disabled={busy || !available || reason.trim().length < 10} onClick={() => void resume()}>Queue reviewed email resumption</Button></>}
    {message && <p role="status">{message}</p>}
  </article>
}

export function EmailHoldReview() {
  const [page, setPage] = useState(1)
  const query = useQuery({queryKey: ['source-email-holds', page], queryFn: ({signal}) => apiFetch<{items: Hold[]}>(`/api/v1/source-review/email-holds?page=${page}`, {signal}), refetchInterval: 5000})
  return <section aria-label="Email follow-up hold review" className="mb-6 rounded-lg border bg-card p-4 space-y-3">
    <h2 className="font-semibold">Email reply holds</h2>
    <p className="text-sm">Review ordinary replies before resuming an existing follow-up sequence. This does not create contact permission or clear STOP, DNC, opt-out, or completed-campaign restrictions. A newer reply requires fresh review.</p>
    {query.isPending && <p role="status">Loading email reply holds…</p>}
    {query.error && <div role="alert"><p>Email reply holds unavailable.</p><Button variant="outline" onClick={() => void query.refetch()}>Retry email holds</Button></div>}
    {query.data?.items.length === 0 && <p>No email reply holds on this page.</p>}
    {query.data?.items.map(hold => <HoldCard key={`${hold.lead_id}:${hold.fingerprint}`} hold={hold} available={!query.isError} refresh={() => void query.refetch()} />)}
    <div className="flex gap-2"><Button variant="outline" disabled={page === 1 || query.isPending} onClick={() => setPage(value => value-1)}>Previous email hold page</Button><Button variant="outline" disabled={query.isPending || (query.data?.items.length ?? 0)<50} onClick={() => setPage(value => value+1)}>Next email hold page</Button></div>
  </section>
}
