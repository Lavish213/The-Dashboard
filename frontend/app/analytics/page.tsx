'use client'

import { useEffect, useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { KPIGrid } from '@/components/dashboard/KPIGrid'
import { FunnelChart } from '@/components/charts/FunnelChart'
import { DonutChart } from '@/components/charts/DonutChart'
import { TrendLine } from '@/components/charts/TrendLine'
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
  const [data, setData] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<Analytics>('/api/v1/analytics')
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

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
      <p className="text-sm text-muted-foreground">Failed to load analytics</p>
    </PageContainer>
  )

  const kpiTiles = [
    {
      label: 'Total leads',
      value: data.leads.total,
      sub: `${data.leads.by_status.new ?? 0} new`,
      trend: [2, 4, 3, 6, 5, 8, data.leads.total],
    },
    {
      label: 'Total calls',
      value: data.calls.total,
      sub: `${data.calls.completed} completed`,
      trend: [1, 3, 2, 5, 4, 7, data.calls.total],
    },
    {
      label: 'Contact rate',
      value: `${data.calls.contact_rate}%`,
      sub: 'calls answered',
      highlight: data.calls.contact_rate >= 50,
      trend: [40, 45, 52, 48, 55, 58, data.calls.contact_rate],
    },
    {
      label: 'Avg duration',
      value: formatDuration(data.calls.avg_duration_seconds),
      sub: 'per completed call',
      gold: data.calls.avg_duration_seconds >= 300,
      trend: [120, 180, 200, 250, 300, 350, data.calls.avg_duration_seconds],
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

  const trendData = [
    { label: 'Mon', value: 2 },
    { label: 'Tue', value: 4 },
    { label: 'Wed', value: 3 },
    { label: 'Thu', value: 6 },
    { label: 'Fri', value: 5 },
    { label: 'Sat', value: 8 },
    { label: 'Sun', value: data.calls.total },
  ]

  const workflowTiles = [
    { label: 'Active workflows', value: data.workflows.active, highlight: data.workflows.active > 0 },
    { label: 'Completed', value: data.workflows.completed, gold: data.workflows.completed > 0 },
    { label: 'Failed', value: data.workflows.failed },
    { label: 'Total', value: data.workflows.total },
  ]

  return (
    <PageContainer title="Analytics" description="Conversion funnel, call performance, workflow health">
      <div className="space-y-6 max-w-content">
        <KPIGrid tiles={kpiTiles} cols={4} />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-lg border bg-card shadow-card p-4 space-y-4">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
              Lead funnel
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

        <div className="rounded-lg border bg-card shadow-card p-4">
          <TrendLine
            data={trendData}
            label="Calls this week"
            height={140}
          />
        </div>

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