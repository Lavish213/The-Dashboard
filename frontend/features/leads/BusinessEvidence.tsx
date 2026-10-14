"use client"

import { useEffect, useState } from 'react'
import { apiFetch } from '@/services/api'

interface Snapshot {
  address: string | null
  apn: string | null
  valuation: { point_cents: number; supported_low_cents: number; supported_high_cents: number; comparable_count: number; purpose: string; as_of: string } | null
  comparables: { sale_id: string | null; source_ref: string; closed_on: string | null; sale_price_cents: number; adjusted_value_cents: number | null }[]
  offers: { id: string | null; status: string; amount_cents: number | null; repairs_cents: number | null }[]
  appointment: { at: string | null; status: string | null }
}
interface Evidence { status: 'current' | 'stale' | 'unavailable'; observed_at?: string; snapshot: Snapshot | null }
const money = (cents: number | null) => cents !== null && Number.isSafeInteger(cents) ? new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(cents / 100) : 'Unverified'

export function BusinessEvidence({leadId}: {leadId: string}) {
  const [evidence, setEvidence] = useState<Evidence | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    async function refresh() {
      try {
        const result = await apiFetch<Evidence>(`/api/v1/leads/${leadId}/business-evidence`)
        if (active) { setEvidence(result); setError(null) }
      } catch { if (active) { setEvidence(null); setError('Property evidence could not be loaded.') } }
    }
    refresh()
    const timer = setInterval(refresh, 30000)
    return () => { active = false; clearInterval(timer) }
  }, [leadId])
  const snapshot = evidence?.snapshot
  return <section className="rounded-lg border bg-card p-5 space-y-3">
    <h2 className="font-semibold">Bob and Sophia property evidence</h2>
    {error ? <p role="alert">{error}</p> : !evidence ? <p role="status">Loading evidence…</p> : !snapshot ? <p>No synchronized property evidence available.</p> : <>
      <p className="text-sm">Snapshot: {evidence.status} · {evidence.observed_at ? new Date(evidence.observed_at).toLocaleString('en-US', {timeZone: 'America/Los_Angeles', timeZoneName: 'short'}) : 'Time unknown'}</p>
      {evidence.status === 'stale' && <p role="alert">This snapshot is stale. Refresh the source before relying on it.</p>}
      <p className="text-sm">{snapshot.address ?? 'Address unverified'} · Parcel {snapshot.apn ?? 'unverified'}</p>
      {snapshot.valuation ? <p>{snapshot.valuation.purpose === 'after_repair' ? 'Reviewed ARV advisory' : 'Reviewed as-is advisory'}: {money(snapshot.valuation.point_cents)} · {money(snapshot.valuation.supported_low_cents)}–{money(snapshot.valuation.supported_high_cents)} · {snapshot.valuation.comparable_count} comps · {snapshot.valuation.as_of}</p> : <p>No current reviewed valuation.</p>}
      <h3 className="font-medium">Comparable evidence</h3>
      {snapshot.comparables.length ? <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr><th scope="col">Source reference</th><th scope="col">Closed</th><th scope="col">Sale price</th><th scope="col">Adjusted indication</th></tr></thead><tbody>{snapshot.comparables.map((row, i) => <tr key={`${row.sale_id}:${i}`}><td>{row.source_ref}</td><td>{row.closed_on ?? 'Unverified'}</td><td>{money(row.sale_price_cents)}</td><td>{money(row.adjusted_value_cents)}</td></tr>)}</tbody></table></div> : <p>No reviewed comparable detail available.</p>}
      <h3 className="font-medium">Recorded offers</h3>
      {snapshot.offers.length ? <ul>{snapshot.offers.map((row, i) => <li key={`${row.id}:${i}`}>{row.status}: {money(row.amount_cents)} · Repairs {money(row.repairs_cents)}</li>)}</ul> : <p>No recorded offers.</p>}
      <h3 className="font-medium">Source appointment</h3>
      <p>{snapshot.appointment.status ?? 'Status unverified'} · {snapshot.appointment.at ? new Date(snapshot.appointment.at).toLocaleString('en-US', {timeZone: 'America/Los_Angeles', timeZoneName: 'short'}) : 'No appointment recorded'}</p>
      <p className="text-xs text-muted-foreground">Read-only source records. Research, draft offers and saved appointment records do not grant offer or contact authority. Confirm current availability before booking.</p>
    </>}
  </section>
}
