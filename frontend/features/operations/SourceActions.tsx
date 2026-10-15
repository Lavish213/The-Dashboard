'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth.store'

type Action = 'set_disposition' | 'cancel_walkthrough' | 'draft_offer'
interface Props { leadId: string; revision: string; appointment: {at: string | null; status: string | null} }
const cents = (value: string) => /^\d+$/.test(value) && Number.isSafeInteger(Number(value) * 100) && Number(value) * 100 <= 10**14 ? Number(value) * 100 : NaN

export function SourceActions({leadId, revision, appointment}: Props) {
  const user = useAuthStore(state => state.user)
  const [action, setAction] = useState<Action>('set_disposition')
  const [disposition, setDisposition] = useState('COLD')
  const [amount, setAmount] = useState('')
  const [repairs, setRepairs] = useState('')
  const [arv, setArv] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [requestId, setRequestId] = useState<string | null>(null)
  const moneyValid = cents(amount) > 0 && Number.isFinite(cents(repairs)) && (!arv || cents(arv) > 0)
  const valid = reason.trim().length >= 10 && (action !== 'draft_offer' || moneyValid) && (action !== 'cancel_walkthrough' || (appointment.status === 'confirmed' && Boolean(appointment.at)))
  const mayWrite = user && ['admin', 'operator'].includes(user.role)
  const commands = useQuery({queryKey: ['source-command-status', leadId], queryFn: ({signal}) => apiFetch<{items: {id: string; state: string; action?: string; error?: string | null}[]}>(`/api/v1/leads/${leadId}/source-commands`, {signal}), enabled: Boolean(mayWrite), refetchInterval: 5000})
  function changed() { setRequestId(null); setMessage('') }
  async function submit() {
    if (!mayWrite || busy || !valid) return
    const identity = requestId ?? crypto.randomUUID()
    setRequestId(identity)
    setBusy(true)
    const data = action === 'set_disposition' ? {disposition} : action === 'cancel_walkthrough' ? {starts_at: appointment.at} : {amount_cents: cents(amount), repair_cents: cents(repairs), arv_cents: arv ? cents(arv) : null}
    try {
      const result = await apiFetch<{state: string}>(`/api/v1/leads/${leadId}/source-operation`, {method: 'POST', body: JSON.stringify({request_id: identity, revision, action, data, reason: reason.trim()})})
      void commands.refetch()
      setMessage(result.state === 'applied' ? 'Source confirmed this operation. Refresh the evidence to see its current state.' : 'Operation queued. It is not confirmed until the source applies it; check source command status below.')
    } catch { setMessage('Operation could not be confirmed. Refresh the source evidence before changing or retrying this request.') }
    finally { setBusy(false) }
  }
  return mayWrite ? <div className="space-y-3 rounded border p-3">
    <h3 className="font-medium">Update Sophia source records</h3>
    <label className="block text-sm">Operation<select value={action} disabled={busy} onChange={event => {setAction(event.target.value as Action); changed()}} className="block rounded border bg-background p-2"><option value="set_disposition">Record seller disposition</option><option value="cancel_walkthrough">Cancel confirmed source walkthrough</option><option value="draft_offer">Create source offer draft</option></select></label>
    {action === 'set_disposition' && <><label className="block text-sm">Disposition<select value={disposition} onChange={event => {setDisposition(event.target.value); changed()}} className="block rounded border bg-background p-2">{['HOT', 'WARM', 'COLD', 'DEAD'].map(value => <option key={value}>{value}</option>)}</select></label><p className="text-xs">DEAD disables calling. Other dispositions do not restore contact permission.</p></>}
    {action === 'cancel_walkthrough' && <p className="text-sm">Only the confirmed reservation shown above can be cancelled. A queued request has not cancelled it yet.</p>}
    {action === 'draft_offer' && <><label className="block text-sm">Draft offer ($, whole dollars)<input inputMode="numeric" value={amount} onChange={event => {setAmount(event.target.value); changed()}} className="block rounded border bg-background p-2" /></label><label className="block text-sm">Repair estimate ($, whole dollars)<input inputMode="numeric" value={repairs} onChange={event => {setRepairs(event.target.value); changed()}} className="block rounded border bg-background p-2" /></label><label className="block text-sm">Reviewed ARV ($, optional whole dollars)<input inputMode="numeric" value={arv} onChange={event => {setArv(event.target.value); changed()}} className="block rounded border bg-background p-2" /></label><p className="text-xs">A draft is not sent to the seller and grants no pricing authority. Use Sophia pricing approval to authorize a call-specific range.</p></>}
    <label className="block text-sm">Operation review reason<textarea value={reason} maxLength={1000} onChange={event => {setReason(event.target.value); changed()}} className="block w-full rounded border bg-background p-2" /></label>
    <Button disabled={busy || !valid} onClick={() => void submit()}>{busy ? 'Queuing…' : 'Queue source operation'}</Button>
    {message && <p role="status">{message}</p>}
    <h4 className="text-sm font-medium">Source command status</h4>
    {commands.isPending && <p role="status">Loading source commands…</p>}
    {commands.error && <p role="alert">Source command status unavailable. Refresh before relying on an operation.</p>}
    {commands.data?.items.length === 0 && <p className="text-sm">No source commands recorded.</p>}
    <ul className="space-y-1 text-sm">{commands.data?.items.map(command => <li key={command.id}>{command.action ?? 'schedule_callback'} · {command.state}{command.error ? ` · ${command.error}` : ''}</li>)}</ul>
  </div> : null
}
