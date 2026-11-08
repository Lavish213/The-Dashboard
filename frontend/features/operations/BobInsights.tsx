'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'

type Readiness = 'HOT_BUY' | 'WATCH_LIST' | 'ARCHIVED' | 'UNGRADED'

interface Deal {
  lead_id: string
  address: string | null
  city: string | null
  distress_score: number | null
  grade: string | null
  readiness: Readiness
  evidence_confidence: string | null
  economics_state: string | null
  limit_method: string | null
  profit_at_asking_cents: number | null
  arv_point_cents: number | null
  asking_price_cents: number | null
  purchase_limit_cents: number | null
  headroom_cents: number | null
  headroom_bps: number | null
  valuation_status: string | null
  valuation_verification: string | null
  comparable_count: number | null
  blocked_count: number | null
  lockout_class: string | null
  next_action: string | null
  graded_at: string | null
}

interface Insights {
  schema_version: number
  generated_at: string
  graded_leads: number
  contactable_leads: number
  briefed_leads: number
  valuation_ready_leads: number
  newest_grade_at: string | null
  newest_grade_age_seconds: number | null
  oldest_grade_age_seconds: number | null
  blocked_leads: number
  economics_unknown_leads: number
  by_readiness: Record<string, number>
  by_grade: Record<string, number>
  by_evidence_confidence: Record<string, number>
  by_lockout_class: Record<string, number>
  by_valuation_verification: Record<string, number>
  deals: Deal[]
  grading_basis: string | null
  quote_authorized: boolean
  offer_authorized: boolean
}

const READINESS_LABEL: Record<Readiness, string> = {
  HOT_BUY: 'Hot buy',
  WATCH_LIST: 'Watch list',
  ARCHIVED: 'Archived',
  UNGRADED: 'Ungraded',
}
const READINESS_COLOR: Record<Readiness, string> = {
  HOT_BUY: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  WATCH_LIST: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  ARCHIVED: 'bg-muted text-muted-foreground border-border',
  UNGRADED: 'bg-muted text-muted-foreground border-border',
}
const EVIDENCE_COLOR: Record<string, string> = {
  verified: 'text-emerald-400',
  supported: 'text-teal-400',
  thin: 'text-amber-400',
  unusable: 'text-red-400',
}
const COUNTS = ['graded_leads', 'contactable_leads', 'briefed_leads', 'valuation_ready_leads', 'blocked_leads', 'economics_unknown_leads'] as const
const MAPS = ['by_readiness', 'by_grade', 'by_evidence_confidence', 'by_lockout_class', 'by_valuation_verification'] as const

export function isInsights(value: unknown): value is Insights {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  if (candidate.schema_version !== 1) return false
  if (!COUNTS.every(key => Number.isInteger(candidate[key]))) return false
  if (!MAPS.every(key => !!candidate[key] && typeof candidate[key] === 'object' && !Array.isArray(candidate[key]))) return false
  return Array.isArray(candidate.deals) && typeof candidate.generated_at === 'string'
}

export function money(cents: number | null) {
  if (cents === null || !Number.isFinite(cents)) return '—'
  return (cents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export function percent(bps: number | null) {
  if (bps === null || !Number.isFinite(bps)) return '—'
  return (bps / 100).toFixed(1) + '%'
}

const STALE_AFTER_SECONDS = 36 * 3600

export function duration(seconds: number) {
  const hours = Math.floor(seconds / 3600)
  if (hours < 48) return `${hours} hour${hours === 1 ? '' : 's'}`
  return `${Math.floor(hours / 24)} days`
}

function words(value: string | null) {
  return value ? value.replaceAll('_', ' ') : '—'
}

async function loadInsights(signal: AbortSignal) {
  const value = await apiFetch<unknown>('/api/v1/bob/insights?limit=25', { signal })
  if (!isInsights(value)) throw new Error('Malformed Bob opportunity report')
  return value
}

function Stat({ label, value, total }: { label: string; value: number; total?: number }) {
  return <div className="rounded border p-3">
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className="text-lg font-semibold tabular-nums">{value.toLocaleString()}{total !== undefined && <span className="text-sm font-normal text-muted-foreground"> / {total.toLocaleString()}</span>}</p>
  </div>
}

function DealRow({ deal }: { deal: Deal }) {
  const readiness = READINESS_LABEL[deal.readiness] ?? deal.readiness
  const address = [deal.address, deal.city].filter(Boolean).join(', ') || 'Address not on file'
  return <tr className="border-t align-top">
    <td className="py-2 pr-2">
      <Link href={`/leads/${deal.lead_id}`} className="font-medium underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{address}</Link>
      <p className="text-xs text-muted-foreground">
        <span className={EVIDENCE_COLOR[deal.evidence_confidence ?? ''] ?? 'text-muted-foreground'}>{words(deal.evidence_confidence)} evidence</span>
        {deal.comparable_count !== null && <> · {deal.comparable_count} comp{deal.comparable_count === 1 ? '' : 's'}</>}
        {deal.distress_score !== null && <> · distress {deal.distress_score}</>}
        {deal.valuation_verification === 'operator_attested' && <> · <span className="text-amber-400">attested, not researched</span></>}
        {deal.valuation_verification === 'independently_retrieved' && <> · <span className="text-emerald-400">source retrieved</span></>}
      </p>
    </td>
    <td className="py-2 pr-2">
      <span className={'inline-block rounded border px-2 py-0.5 text-xs ' + (READINESS_COLOR[deal.readiness] ?? READINESS_COLOR.UNGRADED)}>{readiness}</span>
      <p className="mt-1 text-xs text-muted-foreground">Grade {deal.grade ?? 'none'}</p>
    </td>
    <td className="py-2 pr-2 text-right tabular-nums">{money(deal.arv_point_cents)}</td>
    <td className="py-2 pr-2 text-right tabular-nums">{money(deal.asking_price_cents)}</td>
    <td className="py-2 pr-2 text-right tabular-nums">{money(deal.purchase_limit_cents)}</td>
    <td className={'py-2 pr-6 text-right tabular-nums ' + ((deal.headroom_cents ?? 0) > 0 ? 'text-emerald-400' : 'text-muted-foreground')}>
      {money(deal.headroom_cents)}
      {deal.headroom_bps !== null && <span className="block text-xs font-normal text-muted-foreground">{percent(deal.headroom_bps)} of ARV</span>}
      {deal.limit_method === 'percentage_screen_not_an_underwriting_result' && <span className="block text-xs font-normal text-amber-400">screen only</span>}
    </td>
    <td className="py-2 text-xs">
      <p>{words(deal.next_action)}</p>
      {deal.lockout_class && <p className="text-muted-foreground">held: {words(deal.lockout_class)}</p>}
      {(deal.blocked_count ?? 0) > 0 && <p className="text-red-400">{deal.blocked_count} contact restriction{deal.blocked_count === 1 ? '' : 's'}</p>}
    </td>
  </tr>
}

function Distribution({ label, counts }: { label: string; counts: Record<string, number> }) {
  const entries = Object.entries(counts).filter(([, total]) => Number.isFinite(total))
  if (!entries.length) return null
  return <p className="text-xs text-muted-foreground">
    <span className="font-medium text-foreground">{label}:</span>{' '}
    {entries.sort((a, b) => b[1] - a[1]).map(([key, total]) => `${words(key)} ${total}`).join(' · ')}
  </p>
}

export function BobInsights() {
  const query = useQuery({ queryKey: ['bob-insights'], queryFn: ({ signal }) => loadInsights(signal), refetchInterval: 300000 })
  const report = query.data
  const readiness = report?.by_readiness ?? {}
  return <section className="mb-6 rounded-lg border bg-card p-4 space-y-3" aria-label="Bob opportunity intelligence">
    <div className="flex items-baseline justify-between gap-2">
      <h2 className="font-semibold">Bob opportunity intelligence</h2>
      {report && <span className="text-xs text-muted-foreground">Updated {new Date(report.generated_at).toLocaleString()}</span>}
    </div>
    {query.isPending && <p role="status">Loading Bob opportunity intelligence…</p>}
    {query.error && <div role="alert">
      <p>Bob opportunity intelligence unavailable. No grade is shown rather than a stale one.</p>
      <Button variant="outline" onClick={() => void query.refetch()}>Retry Bob insights</Button>
    </div>}
    {report && <>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <Stat label="Hot buys" value={readiness.HOT_BUY ?? 0} />
        <Stat label="Watch list" value={readiness.WATCH_LIST ?? 0} />
        <Stat label="Archived" value={readiness.ARCHIVED ?? 0} />
        <Stat label="Graded leads" value={report.graded_leads} total={report.contactable_leads} />
        <Stat label="Blocked on contact" value={report.blocked_leads} total={report.graded_leads} />
      </div>
      <p className="text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Coverage:</span>{' '}
        {report.contactable_leads} contactable · {report.briefed_leads} briefed · {report.valuation_ready_leads} with a supported valuation · {report.graded_leads} graded.
        {report.contactable_leads > report.briefed_leads && ` ${report.contactable_leads - report.briefed_leads} contactable lead${report.contactable_leads - report.briefed_leads === 1 ? ' has' : 's have'} no brief yet, so Bob has not looked at ${report.contactable_leads - report.briefed_leads === 1 ? 'it' : 'them'}.`}
      </p>
      <Distribution label="Grades" counts={report.by_grade} />
      <Distribution label="Evidence confidence" counts={report.by_evidence_confidence} />
      <Distribution label="Held for" counts={report.by_lockout_class} />
      <Distribution label="Evidence provenance" counts={report.by_valuation_verification} />
      {(report.by_valuation_verification.operator_attested ?? 0) > 0 && <p className="text-xs text-amber-400">
        {report.by_valuation_verification.operator_attested} graded lead{(report.by_valuation_verification.operator_attested ?? 0) === 1 ? ' rests' : 's rest'} on comparable evidence someone asserted rather than evidence Bob retrieved and checksummed. The gates above were applied to those facts; they were not independently verified.
      </p>}
      {report.graded_leads > 0 && report.newest_grade_age_seconds !== null && report.newest_grade_age_seconds > STALE_AFTER_SECONDS && <p role="alert" className="text-sm text-red-400">
        Bob has not graded anything in {duration(report.newest_grade_age_seconds)}. Briefs refresh roughly every 24 hours, so this usually means the Bob worker has stopped. Treat every grade below as stale.
      </p>}
      {report.economics_unknown_leads > 0 && <p role="alert" className="text-sm text-amber-400">
        {report.economics_unknown_leads} graded lead{report.economics_unknown_leads === 1 ? '' : 's'} still lack a repair estimate or asking price, so no purchase limit was computed. Missing figures are shown as an em dash, never as zero.
      </p>}
      {report.deals.length === 0
        ? <p className="text-sm text-muted-foreground">Bob has not graded any opportunities yet. Grades appear once a lead has a call brief with comparable evidence.</p>
        : <div className="overflow-x-auto">
          <table className="w-full min-w-[56rem] text-sm">
            <caption className="sr-only">Bob graded opportunities, highest headroom first</caption>
            <thead><tr className="text-left text-muted-foreground">
              <th className="py-1 font-medium">Property</th>
              <th className="py-1 font-medium">Readiness</th>
              <th className="py-1 text-right font-medium">ARV</th>
              <th className="py-1 text-right font-medium">Asking</th>
              <th className="py-1 text-right font-medium">Purchase limit</th>
              <th className="py-1 pr-6 text-right font-medium">Headroom</th>
              <th className="py-1 font-medium">Next action</th>
            </tr></thead>
            <tbody>{report.deals.map(deal => <DealRow key={deal.lead_id + (deal.graded_at ?? '')} deal={deal} />)}</tbody>
          </table>
        </div>}
      <p className="text-xs text-muted-foreground">
        A purchase limit marked &quot;screen only&quot; is a flat percentage of ARV less repairs; it over-reserves on light rehabs and under-reserves on heavy ones. Supply itemised holding, financing and selling costs and the limit is solved from them instead.
      </p>
      <p className="text-xs text-muted-foreground">
        Screening estimates from Bob&apos;s comparable evidence, not an appraisal and not an investment guarantee. A grade is capped by its evidence confidence, so strong economics on thin evidence never reads as a hot buy. Purchase limit is a screening figure; it is not an approved offer, and nothing here authorizes a quote or an offer.
      </p>
    </>}
  </section>
}
