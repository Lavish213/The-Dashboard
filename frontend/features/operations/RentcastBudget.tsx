'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth.store'

const HARD_CAP = 50

interface Usage { used: number; hard_cap: number; window_days: number; enabled: boolean; configured_cap: number; remaining: number }
interface Result { requested: number; priced: number; no_data: number; errors: number; comps_saved: number; stopped: string | null }

function isUsage(value: unknown): value is Usage {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  return ['used', 'hard_cap', 'window_days', 'configured_cap', 'remaining'].every(key => Number.isInteger(candidate[key])) && typeof candidate.enabled === 'boolean'
}

async function loadUsage(signal: AbortSignal) {
  const value = await apiFetch<unknown>('/api/v1/source-review/rentcast/usage', { signal })
  if (!isUsage(value)) throw new Error('Malformed RentCast usage')
  return value
}

export function RentcastBudget() {
  const user = useAuthStore(state => state.user)
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['rentcast-usage'], queryFn: ({ signal }) => loadUsage(signal), refetchInterval: 300000 })
  const [count, setCount] = useState(10)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const usage = query.data
  const remaining = usage ? Math.max(0, Math.min(usage.remaining, HARD_CAP - usage.used)) : 0
  const size = Math.max(1, Math.min(count, remaining || 1))
  async function price() {
    setBusy(true)
    setMessage('')
    try {
      const result = await apiFetch<Result>('/api/v1/source-review/rentcast/price', { method: 'POST', body: JSON.stringify({ limit: size }) })
      setMessage(`Priced ${result.priced}, no data ${result.no_data}, errors ${result.errors}, listing comps saved ${result.comps_saved}.${result.stopped ? ` Stopped: ${result.stopped}.` : ''}`)
    } catch {
      setMessage('Pricing could not be confirmed. Check the usage count before trying again.')
    } finally {
      setBusy(false)
      void client.invalidateQueries({ queryKey: ['rentcast-usage'] })
      void client.invalidateQueries({ queryKey: ['data-quality'] })
    }
  }
  return <section className="mb-6 rounded-lg border bg-card p-4 space-y-3" aria-label="RentCast budget">
    <h2 className="font-semibold">RentCast pricing</h2>
    {query.isPending && <p role="status">Loading RentCast usage…</p>}
    {query.error && <div role="alert"><p>RentCast usage unavailable.</p><Button variant="outline" onClick={() => void query.refetch()}>Retry RentCast usage</Button></div>}
    {usage && <>
      <p className="text-lg font-semibold tabular-nums">RentCast calls used: {usage.used} / {HARD_CAP}</p>
      <p className="text-sm text-muted-foreground">Rolling {usage.window_days} day window. {remaining} calls left. The database refuses call {HARD_CAP + 1}.</p>
      {!usage.enabled && <p className="text-sm">RentCast is off. Set RENTCAST_ENABLED to true on Sophia to allow pricing.</p>}
      {usage.enabled && user?.role === 'admin' && remaining > 0 && <div className="flex flex-wrap items-end gap-2">
        <label className="text-sm">Houses to price<input type="number" min={1} max={remaining} value={size} onChange={event => setCount(Number.parseInt(event.target.value, 10) || 1)} className="ml-2 w-20 rounded border bg-background p-1" /></label>
        <Button disabled={busy} onClick={() => void price()}>{busy ? 'Pricing…' : `Price next ${size}`}</Button>
      </div>}
      {usage.enabled && remaining === 0 && <p role="alert">No RentCast calls left in this window.</p>}
      {message && <p role="status" className="text-sm">{message}</p>}
      <p className="text-xs text-muted-foreground">RentCast values come from listing prices, not recorded sales. Check them against MLS comps before any offer.</p>
    </>}
  </section>
}
