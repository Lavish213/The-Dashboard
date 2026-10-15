'use client'

import { SourceOperations } from '@/features/operations/SourceOperations'

import { useLeadPages } from '@/hooks/data/useLeadPages'
import { useRouter } from 'next/navigation'
import { PageContainer } from '@/components/workspace/PageContainer'
import { Button } from '@/components/ui/button'
import { scoreColor, STATUS_COLORS } from '@/constants/colors'
import { LeadAvatar } from '@/components/leads/LeadAvatar'
import { TrendingUp, DollarSign, Home, Clock, type LucideIcon } from 'lucide-react'

interface Deal {
  id: string
  full_name: string
  phone: string | null
  lead_status: string
  ai_score: number | null
  address: string | null
  city: string | null
  state: string | null
  follow_up_at: string | null
  created_at: string
  updated_at: string
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function DealCard({ deal, onClick }: { deal: Deal; onClick: () => void }) {
  const sc = scoreColor(deal.ai_score)
  const address = [deal.address, deal.city, deal.state].filter(Boolean).join(', ')

  return (
    <button type="button"
      onClick={onClick}
      className="w-full text-left rounded-lg border bg-card shadow-card p-4 space-y-3 cursor-pointer hover:border-teal-500/30 hover:shadow-card-hover transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="flex items-start gap-3">
        <LeadAvatar name={deal.full_name} score={deal.ai_score} size="md" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground truncate font-display">
            {deal.full_name}
          </p>
          {address && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{address}</p>
          )}
          {deal.phone && (
            <p className="text-xs text-muted-foreground font-mono mt-0.5">{deal.phone}</p>
          )}
        </div>
        {deal.ai_score != null && (
          <span className={`text-sm font-bold tabular-nums flex-shrink-0 ${sc.text}`}>
            {deal.ai_score}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-border">
        <span className={`rounded border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[deal.lead_status] ?? 'bg-muted text-muted-foreground border-border'}`}>
          {deal.lead_status}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatDate(deal.updated_at)}
        </span>
      </div>
    </button>
  )
}

function StatTile({ icon: Icon, label, value, color }: {
  icon: LucideIcon; label: string; value: string | number; color: string
}) {
  return (
    <div className="rounded-lg border bg-card shadow-card p-4 flex items-center gap-3">
      <div className={`h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-xl font-semibold tabular-nums text-foreground">{value}</p>
      </div>
    </div>
  )
}

export default function DealsPage() {
  const router = useRouter()
  const { data, isPending: loading, error, hasNextPage, fetchNextPage, isFetchingNextPage } = useLeadPages<Deal>({ statuses: 'qualified' })
  const convertedQuery = useLeadPages<Deal>({ statuses: 'converted' })
  const deals = [...(data?.pages.flatMap(page => page.items) ?? []), ...(convertedQuery.data?.pages.flatMap(page => page.items) ?? [])]

  const qualified = deals.filter(d => d.lead_status === 'qualified')
  const converted = deals.filter(d => d.lead_status === 'converted')
  const qualifiedTotal = data?.pages[0].total
  const convertedTotal = convertedQuery.data?.pages[0].total
  const completeTotals = qualifiedTotal !== undefined && convertedTotal !== undefined
  const total = (qualifiedTotal ?? 0) + (convertedTotal ?? 0)
  const avgScore = total ? Math.round(((data?.pages[0].summary?.score_total ?? 0) + (convertedQuery.data?.pages[0].summary?.score_total ?? 0)) / total) : 0

  return (
    <PageContainer title="Deals" description="Active pipeline — qualified leads and closed deals">
      <SourceOperations view="deals" />
      {(error || convertedQuery.error) && <p role="alert" className="mb-4 text-sm text-destructive">Deals unavailable. Existing values may be stale.</p>}
      {completeTotals && <p role="status" className="mb-4 text-sm text-muted-foreground">Loaded {deals.length} of {total} deals. Totals cover all matching records.</p>}
      {hasNextPage && <Button variant="outline" className="mb-4 mr-2" disabled={isFetchingNextPage} onClick={() => void fetchNextPage()}>Load more qualified deals</Button>}
      {convertedQuery.hasNextPage && <Button variant="outline" className="mb-4" disabled={convertedQuery.isFetchingNextPage} onClick={() => void convertedQuery.fetchNextPage()}>Load more converted deals</Button>}
      <div className="space-y-6 max-w-content">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile icon={TrendingUp} label="Total deals" value={completeTotals ? total : '—'} color="bg-teal-500/10 text-teal-400" />
          <StatTile icon={Home} label="Qualified" value={qualifiedTotal ?? '—'} color="bg-amber-500/10 text-amber-400" />
          <StatTile icon={DollarSign} label="Converted" value={convertedTotal ?? '—'} color="bg-green-500/10 text-green-400" />
          <StatTile icon={Clock} label="Avg score" value={completeTotals ? avgScore : '—'} color="bg-blue-500/10 text-blue-400" />
        </div>

        {loading || convertedQuery.isPending ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-32 rounded-lg border bg-card animate-pulse" />
            ))}
          </div>
        ) : !error && !convertedQuery.error && deals.length === 0 ? (
          <div className="rounded-lg border bg-card p-10 text-center shadow-card">
            <TrendingUp className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm font-medium text-foreground">No deals yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Leads move here when Sophia qualifies them
            </p>
          </div>
        ) : (
          <>
            {qualified.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Qualified — {qualified.length}
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {qualified.map(deal => (
                    <DealCard
                      key={deal.id}
                      deal={deal}
                      onClick={() => router.push(`/leads/${deal.id}`)}
                    />
                  ))}
                </div>
              </div>
            )}
            {converted.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Converted — {converted.length}
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {converted.map(deal => (
                    <DealCard
                      key={deal.id}
                      deal={deal}
                      onClick={() => router.push(`/leads/${deal.id}`)}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </PageContainer>
  )
}
