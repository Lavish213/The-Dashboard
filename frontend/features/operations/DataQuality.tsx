'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'

interface Bucket { properties: number; with_comp_arv: number; needs_comps: number }
interface Report {
  generated_at: string
  properties: number
  properties_with_comp_arv: number
  properties_needing_comps: number
  assessed_based_arv: number
  comps_rows: number
  leads: number
  leads_with_phone: number
  leads_with_bob_brief: number
  by_distress_type: Record<string, Bucket>
}

function Stat({ label, value, total }: { label: string; value: number; total?: number }) {
  return <div className="rounded border p-3">
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className="text-lg font-semibold tabular-nums">{value.toLocaleString()}{total !== undefined && <span className="text-sm font-normal text-muted-foreground"> / {total.toLocaleString()}</span>}</p>
  </div>
}

const COUNTS = ['properties', 'properties_with_comp_arv', 'properties_needing_comps', 'assessed_based_arv', 'comps_rows', 'leads', 'leads_with_phone', 'leads_with_bob_brief'] as const

function isReport(value: unknown): value is Report {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  return COUNTS.every(key => Number.isInteger(candidate[key])) && typeof candidate.generated_at === 'string' && !!candidate.by_distress_type && typeof candidate.by_distress_type === 'object' && !Array.isArray(candidate.by_distress_type)
}

async function loadReport(signal: AbortSignal) {
  const value = await apiFetch<unknown>('/api/v1/source-review/data-quality', { signal })
  if (!isReport(value)) throw new Error('Malformed data quality report')
  return value
}

export function DataQuality() {
  const query = useQuery({ queryKey: ['data-quality'], queryFn: ({ signal }) => loadReport(signal), refetchInterval: 300000 })
  const report = query.data
  return <section className="mb-6 rounded-lg border bg-card p-4 space-y-3" aria-label="Data quality">
    <h2 className="font-semibold">Data quality</h2>
    {query.isPending && <p role="status">Loading data quality…</p>}
    {query.error && <div role="alert"><p>Data quality report unavailable.</p><Button variant="outline" onClick={() => void query.refetch()}>Retry data quality</Button></div>}
    {report && <>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Leads with a phone" value={report.leads_with_phone} total={report.leads} />
        <Stat label="Properties with comp ARV" value={report.properties_with_comp_arv} total={report.properties} />
        <Stat label="Closed sale comps on file" value={report.comps_rows} />
        <Stat label="Leads with a Bob brief" value={report.leads_with_bob_brief} total={report.leads} />
      </div>
      {report.assessed_based_arv > 0 && <p role="alert">{report.assessed_based_arv} properties still carry an ARV derived from tax assessed value. Do not use them for offers.</p>}
      <table className="w-full text-sm">
        <caption className="sr-only">Pricing coverage by distress type</caption>
        <thead><tr className="text-left text-muted-foreground"><th className="py-1 font-medium">Distress type</th><th className="py-1 text-right font-medium">Properties</th><th className="py-1 text-right font-medium">Comp ARV</th><th className="py-1 text-right font-medium">Needs comps</th></tr></thead>
        <tbody>{Object.entries(report.by_distress_type).map(([kind, bucket]) => <tr key={kind} className="border-t"><td className="py-1">{kind.replaceAll('_', ' ')}</td><td className="py-1 text-right tabular-nums">{bucket.properties}</td><td className="py-1 text-right tabular-nums">{bucket.with_comp_arv}</td><td className="py-1 text-right tabular-nums">{bucket.needs_comps}</td></tr>)}</tbody>
      </table>
      <p className="text-xs text-muted-foreground">Generated {new Date(report.generated_at).toLocaleString()}. Refreshes every 5 minutes. ARV is shown only when built from closed sale comps.</p>
    </>}
  </section>
}
