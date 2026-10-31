'use client'

import { useState } from 'react'
import { EmailHoldReview } from '@/features/operations/EmailHoldReview'
import { DeliveryEvidence } from '@/features/operations/DeliveryEvidence'
import { ConnectionStatus } from '@/features/operations/ConnectionStatus'
import { DataQuality } from '@/features/operations/DataQuality'
import { PriceReview } from '@/features/operations/PriceReview'
import { WorkflowReview } from '@/features/operations/WorkflowReview'
import { useQuery } from '@tanstack/react-query'
import { PageContainer } from '@/components/workspace/PageContainer'
import { Button } from '@/components/ui/button'
import { apiFetch } from '@/services/api'
import { useAuthStore } from '@/stores/auth.store'

interface Candidate { fingerprint: string; id: string; source: string; source_ref: string; status: string; observed_at: string; payload: Record<string, unknown> }

function CandidateCard({ candidate, refresh }: { candidate: Candidate; refresh: () => void }) {
  const user = useAuthStore(state => state.user)
  const [reason, setReason] = useState('')
  const [lead, setLead] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function review(decision: string) {
    setBusy(true)
    try {
      await apiFetch(`/api/v1/source-review/candidates/${candidate.id}/review`, { method: 'POST', body: JSON.stringify({ decision, reason, fingerprint: candidate.fingerprint, lead_id: decision === 'dismissed' ? null : lead }) })
      setMessage('Source review saved. Contact and offer authority remain unchanged.')
      refresh()
    } catch { setMessage('Review could not be confirmed. Refresh before retrying.') }
    finally { setBusy(false) }
  }
  return <article className="rounded-lg border bg-card p-4 space-y-3">
    <h2 className="font-semibold">{candidate.source} · {candidate.status.replaceAll('_', ' ')}</h2>
    <p className="text-sm break-all">Source reference: {candidate.source_ref}</p>
    <p className="text-sm text-muted-foreground">Observed {new Date(candidate.observed_at).toLocaleString()}</p>
    <details><summary className="cursor-pointer">Raw source information</summary><pre className="whitespace-pre-wrap break-all text-xs">{JSON.stringify(candidate.payload, null, 2).slice(0, 4000)}</pre></details>
    {candidate.status === 'needs_property_review' && user && ['admin', 'operator'].includes(user.role) && <div className="space-y-2">
      <label className="block text-sm">Review reason<textarea value={reason} onChange={event => setReason(event.target.value)} maxLength={1000} className="block w-full rounded border bg-background p-2" /></label>
      <label className="block text-sm">Existing Sophia lead UUID<input value={lead} onChange={event => setLead(event.target.value)} className="block w-full rounded border bg-background p-2" /></label>
      <Button variant="outline" disabled={busy || reason.length < 10} onClick={() => void review('dismissed')}>Dismiss candidate</Button>
      <Button className="ml-2" disabled={busy || reason.length < 10 || !lead} onClick={() => void review('linked_to_reviewed_lead')}>Link existing lead</Button>
    </div>}
    {message && <p role="status">{message}</p>}
  </article>
}

export default function SourceReviewPage() {
  const [page, setPage] = useState(1)
  const query = useQuery({queryKey: ['source-review', page], queryFn: ({signal}) => apiFetch<{items: Candidate[]}>(`/api/v1/source-review/candidates?page=${page}`, {signal})})
  return <PageContainer title="Source review" description="Unverified discovery candidates. Linking records does not authorize contact, offers, or property pricing.">
    <ConnectionStatus />
    <DataQuality />
    <DeliveryEvidence />
    <EmailHoldReview />
    <PriceReview />
    <WorkflowReview />
    {query.isPending && <p role="status">Loading source candidates…</p>}
    {query.error && <div role="alert"><p>Source candidates unavailable.</p><Button variant="outline" onClick={() => void query.refetch()}>Retry</Button></div>}
    {query.data && query.data.items.length === 0 && <p>No candidates on this page.</p>}
    <div className="space-y-4">{query.data?.items.map(candidate => <CandidateCard key={candidate.id} candidate={candidate} refresh={() => void query.refetch()} />)}</div>
    <div className="mt-4 flex gap-2"><Button variant="outline" disabled={page === 1 || query.isPending} onClick={() => setPage(value => value - 1)}>Previous page</Button><Button variant="outline" disabled={query.isPending || (query.data?.items.length ?? 0) < 50} onClick={() => setPage(value => value + 1)}>Next page</Button></div>
  </PageContainer>
}
