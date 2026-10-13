'use client'

import { useQuery } from '@tanstack/react-query'
import { PageContainer } from '@/components/workspace/PageContainer'
import { KPIGrid } from '@/components/dashboard/KPIGrid'
import { FunnelChart } from '@/components/charts/FunnelChart'
import { DonutChart } from '@/components/charts/DonutChart'
import { apiFetch } from '@/services/api'

interface Analytics {
  leads: {
    total: number
    by_status: Record<string, number>
  }
  calls: {
    total: number
    completed: number
    no_answer: number
    voicemail: number
    failed: number
    contact_rate: number
    avg_duration_seconds: number
  }
  workflows: {
    total: number
    active: number
    completed: number
    failed: number
  }
}

function formatDuration(s: number): string {
  if (s >= 60) return `${Math.floor(s / 60)}m ${s % 60}s`
  return `${s}s`
}

export default function AnalyticsPage() {
  const { data, isPending: loading, error, refetch } = useQuery({ queryKey: ['dashboard-analytics'], queryFn: ({ signal }) => apiFetch<Analytics>('/api/v1/analytics', { signal }), refetchInterval: 30_000 })

  if (loading) {
    return (
      <PageContainer title="Analytics" description="Performance metrics">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 rounded-lg border bg-card animate-pulse" />
            ))}
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="h-64 rounded-lg border bg-card animate-pulse" />
            <div className="h-64 rounded-lg border bg-card animate-pulse" />
          </div>
        </div>
      </PageContainer>
    )
  }

  if (!data) return (
    <PageContainer title="Analytics" description="Performance metrics">
      <p role="alert" className="text-sm text-destructive">Analytics unavailable.</p>
      <button onClick={() => void refetch()} className="mt-3 text-sm underline">Retry analytics</button>
    </PageContainer>
  )

  const kpiTiles = [
    {
      label: 'Total leads',
      value: data.leads.total,
      sub: `${data.leads.by_status.new ?? 0} new`,
    },
    {
      label: 'Total calls',
      value: data.calls.total,
      sub: `${data.calls.completed} completed`,
    },
    {
      label: 'Contact rate',
      value: `${data.calls.contact_rate}%`,
      sub: 'calls answered',
      highlight: data.calls.contact_rate >= 50,
    },
    {
      label: 'Avg duration',
      value: formatDuration(data.calls.avg_duration_seconds),
      sub: 'per completed call',
      gold: data.calls.avg_duration_seconds >= 300,
    },
  ]

  const funnelBars = [
    { label: 'New', value: data.leads.by_status.new ?? 0, max: data.leads.total, color: 'bg-teal-500' },
    { label: 'Contacted', value: data.leads.by_status.contacted ?? 0, max: data.leads.total, color: 'bg-blue-500' },
    { label: 'Qualified', value: data.leads.by_status.qualified ?? 0, max: data.leads.total, color: 'bg-amber-500' },
    { label: 'Converted', value: data.leads.by_status.converted ?? 0, max: data.leads.total, color: 'bg-green-500' },
    { label: 'Dead', value: data.leads.by_status.dead ?? 0, max: data.leads.total, color: 'bg-red-500' },
  ]

  const donutData = [
    { name: 'Completed', value: data.calls.completed, color: '#22c55e' },
    { name: 'Voicemail', value: data.calls.voicemail, color: '#f59e0b' },
    { name: 'No answer', value: data.calls.no_answer, color: '#6b7280' },
    { name: 'Failed', value: data.calls.failed, color: '#ef4444' },
  ].filter(d => d.value > 0)

  const workflowTiles = [
    { label: 'Active workflows', value: data.workflows.active, highlight: data.workflows.active > 0 },
    { label: 'Completed', value: data.workflows.completed, gold: data.workflows.completed > 0 },
    { label: 'Failed', value: data.workflows.failed },
    { label: 'Total', value: data.workflows.total },
  ]

  return (
    <PageContainer title="Analytics" description="All-time lead status, call outcomes and workflow totals">
      <div className="space-y-6 max-w-content">
        {error && <p role="alert" className="text-sm text-destructive">Analytics refresh failed. Displayed values may be stale.</p>}
        <KPIGrid tiles={kpiTiles} cols={4} />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-lg border bg-card shadow-card p-4 space-y-4">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
              Lead status distribution
            </p>
            <FunnelChart bars={funnelBars} />
          </div>

          <div className="rounded-lg border bg-card shadow-card p-4 space-y-4">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
              Call outcomes
            </p>
            {donutData.length > 0 ? (
              <DonutChart data={donutData} height={220} />
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">No call data yet</p>
            )}
          </div>
        </div>

        <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">Historical trends are unavailable. The analytics API currently provides totals without daily observations.</p>

        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-3">
            Workflows
          </p>
          <KPIGrid tiles={workflowTiles} cols={4} />
        </div>
      </div>
    </PageContainer>
  )
}
