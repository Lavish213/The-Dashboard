'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth.store'

interface Job { id: string; lead_id: string; error: string | null }
interface Health { status: string; requires_review: number; review_owner_configured: boolean; items: Job[] }

function ReviewJob({ job, refresh }: { job: Job; refresh: () => void }) {
  const user = useAuthStore(state => state.user)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function skip() {
    setBusy(true)
    try {
      await apiFetch(`/api/v1/source-review/workflow-review/${job.id}/reconcile`, {method: 'POST', body: JSON.stringify({decision: 'skipped', reason})})
      setMessage('Reconciliation saved. This job will not be resent.')
      refresh()
    } catch { setMessage('Reconciliation could not be confirmed. The job remains blocked until reviewed.') }
    finally { setBusy(false) }
  }
  return <li className="border-t py-3 space-y-2">
    <p className="text-sm break-all">Job {job.id} · Source lead {job.lead_id}</p>
    <p className="text-sm">{job.error ?? 'Provider outcome requires review'}</p>
    {user && ['admin', 'operator'].includes(user.role) && <><label className="block text-sm">Reconciliation reason<textarea className="block w-full rounded border bg-background p-2" value={reason} maxLength={1000} onChange={event => setReason(event.target.value)} /></label><Button variant="outline" disabled={busy || reason.length < 10} onClick={() => void skip()}>Record review and skip</Button></>}
    {message && <p role="status">{message}</p>}
  </li>
}

export function WorkflowReview() {
  const query = useQuery({queryKey: ['workflow-review'], queryFn: ({signal}) => apiFetch<Health>('/api/v1/source-review/workflow-review', {signal}), refetchInterval: 30000})
  return <section className="mb-6 rounded-lg border bg-card p-4 space-y-3" aria-label="Workflow recovery review">
    <h2 className="font-semibold">Workflow recovery</h2>
    {query.isPending && <p role="status">Loading recovery status…</p>}
    {query.error && <div role="alert"><p>Recovery status unavailable.</p><Button variant="outline" onClick={() => void query.refetch()}>Retry recovery status</Button></div>}
    {query.data && <><p>{query.data.requires_review} uncertain jobs require review · {query.data.status}</p>{!query.data.review_owner_configured && <p role="alert">A review owner has not been configured.</p>}<ul>{query.data.items.map(job => <ReviewJob key={job.id} job={job} refresh={() => void query.refetch()} />)}</ul></>}
  </section>
}
