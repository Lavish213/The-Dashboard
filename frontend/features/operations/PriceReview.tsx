'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth.store'

interface Review { id: string; lead_id: string; property_id: string; address: string | null; call_sid: string | null; requested_action: string; expires_at: string; risk_reason: string; fingerprint: string }

function ReviewCard({ review, available, refresh }: { review: Review; available: boolean; refresh: () => void }) {
  const user = useAuthStore(state => state.user)
  const [low, setLow] = useState('')
  const [high, setHigh] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer) }, [])
  const expiry = Date.parse(review.expires_at)
  const expired = !Number.isFinite(expiry) || expiry <= now
  const lowCents = /^\d+$/.test(low) ? Number(low) * 100 : NaN
  const highCents = /^\d+$/.test(high) ? Number(high) * 100 : NaN
  const rangeValid = Number.isSafeInteger(lowCents) && Number.isSafeInteger(highCents) && lowCents > 0 && lowCents <= highCents && highCents <= 10**14
  const canDecide = user && ['admin', 'reviewer'].includes(user.role)
  async function decide(status: 'approved' | 'rejected') {
    if (busy || expired || !available || reason.trim().length < 10 || (status === 'approved' && !rangeValid)) return
    setBusy(true)
    try {
      const result = await apiFetch<{persisted: boolean; approval_id: string; status: string}>(`/api/v1/source-review/price-reviews/${encodeURIComponent(review.id)}/resolve`, {method: 'POST', body: JSON.stringify({status, reason: reason.trim(), fingerprint: review.fingerprint, offer_low_cents: status === 'approved' ? lowCents : null, offer_high_cents: status === 'approved' ? highCents : null})})
      if (!result.persisted || result.approval_id !== review.id || result.status !== status) throw new Error('Unconfirmed source receipt')
      setMessage(`Source confirmed this decision: ${status}.`)
      refresh()
    } catch { setMessage('Decision not confirmed. Refresh the source review before retrying.') }
    finally { setBusy(false) }
  }
  return <article className="rounded border p-4 space-y-3">
    <h3 className="font-medium">{review.address ?? 'Address unverified'}</h3>
    <p className="text-sm break-all">Source lead {review.lead_id} · Property {review.property_id}</p>
    <p className="text-sm break-all">Action: {review.requested_action} · Call: {review.call_sid ?? 'Unverified'}</p>
    <p className="text-sm">Expires {Number.isFinite(expiry) ? new Date(expiry).toLocaleString('en-US', {timeZone: 'America/Los_Angeles', timeZoneName: 'short'}) : 'time unverified'}</p>
    <p className="text-sm">{review.risk_reason}</p>
    {expired && <p role="alert">This review expired. Sophia needs a new request before pricing can be authorized.</p>}
    {canDecide && <div className="space-y-2">
      <label className="block text-sm">Approved minimum offer ($, whole dollars)<input inputMode="numeric" value={low} onChange={event => setLow(event.target.value)} className="block rounded border bg-background p-2" /></label>
      <label className="block text-sm">Approved maximum offer ($, whole dollars)<input inputMode="numeric" value={high} onChange={event => setHigh(event.target.value)} className="block rounded border bg-background p-2" /></label>
      <label className="block text-sm">Pricing review reason<textarea value={reason} maxLength={1000} onChange={event => setReason(event.target.value)} className="block w-full rounded border bg-background p-2" /></label>
      <Button disabled={busy || expired || !available || reason.trim().length < 10 || !rangeValid} onClick={() => void decide('approved')}>Approve this price range</Button>
      <Button variant="outline" className="ml-2" disabled={busy || expired || !available || reason.trim().length < 10} onClick={() => void decide('rejected')}>Reject pricing request</Button>
    </div>}
    {message && <p role="status">{message}</p>}
  </article>
}

export function PriceReview() {
  const [page, setPage] = useState(1)
  const query = useQuery({queryKey: ['source-price-reviews', page], queryFn: ({signal}) => apiFetch<{items: Review[]}>(`/api/v1/source-review/price-reviews?page=${page}`, {signal}), refetchInterval: 5000})
  return <section className="mb-6 rounded-lg border bg-card p-4 space-y-3" aria-label="Sophia pricing review">
    <h2 className="font-semibold">Sophia pricing approval</h2>
    <p className="text-sm">Review the property, comps and repair scope before granting a range. Approval is limited to the listed call, action, property and expiry. Contact permission remains separate.</p>
    {query.isPending && <p role="status">Loading pricing requests…</p>}
    {query.error && <div role="alert"><p>Current pricing reviews unavailable.</p><Button variant="outline" onClick={() => void query.refetch()}>Retry pricing reviews</Button></div>}
    {query.data?.items.length === 0 && <p>No current pricing requests on this page.</p>}
    {query.data?.items.map(review => <ReviewCard key={`${review.id}:${review.fingerprint}`} review={review} available={!query.isError} refresh={() => void query.refetch()} />)}
    <div className="flex gap-2"><Button variant="outline" disabled={page === 1 || query.isPending} onClick={() => setPage(value => value - 1)}>Previous pricing page</Button><Button variant="outline" disabled={query.isPending || (query.data?.items.length ?? 0) < 50} onClick={() => setPage(value => value + 1)}>Next pricing page</Button></div>
  </section>
}
