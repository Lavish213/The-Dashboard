'use client'

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { PageContainer } from '@/components/workspace/PageContainer'
import { KPIGrid } from '@/components/dashboard/KPIGrid'
import { SophiaStatusWidget } from '@/components/dashboard/SophiaStatusWidget'
import { SocialWidget } from '@/components/dashboard/SocialWidget'
import { apiFetch } from '@/services/api'
import { useSophiaStore } from '@/stores/sophia.store'
import { getSignals } from '@/services/sophia'

interface Analytics {
  leads: { total: number; by_status: Record<string, number> }
  calls: { total: number; completed: number; contact_rate: number; avg_duration_seconds: number }
  workflows: { total: number; active: number; completed: number }
}

interface ActiveCall {
  session_id: string | null
  caller_name: string | null
  phone: string | null
  duration_seconds: number
}

export default function DashboardPage() {
  const { setSignals, setSessionId } = useSophiaStore()
  const analyticsQuery = useQuery({
    queryKey: ['dashboard-analytics'],
    queryFn: ({ signal }) => apiFetch<Analytics>('/api/v1/analytics', { signal }),
    refetchInterval: 30_000,
  })
  const callsQuery = useQuery({
    queryKey: ['dashboard-connected-calls'],
    queryFn: ({ signal }) => apiFetch<{ items: { id: string; sophia_session_id: string | null; duration_seconds: number | null }[] }>(
      '/api/v1/calls?call_status=connected&page_size=1', { signal }),
    refetchInterval: 5_000,
  })
  const call = callsQuery.isError ? null : callsQuery.data?.items[0]
  const sessionId = call?.sophia_session_id ?? null
  const activeCall: ActiveCall | null = call ? {
    session_id: sessionId, caller_name: null, phone: null, duration_seconds: call.duration_seconds ?? 0,
  } : null
  const signalQuery = useQuery({
    queryKey: ['dashboard-signals', sessionId],
    queryFn: () => getSignals(sessionId!),
    enabled: Boolean(sessionId),
    refetchInterval: 10_000,
  })
  useEffect(() => { setSessionId(sessionId) }, [sessionId, setSessionId])
  useEffect(() => {
    if (useSophiaStore.getState().sessionId === sessionId) {
      setSignals(signalQuery.isError ? null : signalQuery.data ?? null)
    }
  }, [sessionId, signalQuery.data, signalQuery.isError, setSignals])
  const analytics = analyticsQuery.data

  const kpiTiles = analytics
    ? [
        {
          label: 'Total leads',
          value: analytics.leads.total,
          sub: `${analytics.leads.by_status.new ?? 0} new`,
          highlight: false,
        },
        {
          label: 'Total calls',
          value: analytics.calls.total,
          sub: `${analytics.calls.completed} completed`,
        },
        {
          label: 'Contact rate',
          value: `${analytics.calls.contact_rate}%`,
          sub: 'calls answered',
          highlight: analytics.calls.contact_rate >= 50,
        },
        {
          label: 'Avg call duration',
          value: analytics.calls.avg_duration_seconds >= 60
            ? `${Math.floor(analytics.calls.avg_duration_seconds / 60)}m ${analytics.calls.avg_duration_seconds % 60}s`
            : `${analytics.calls.avg_duration_seconds}s`,
          sub: 'per completed call',
          gold: analytics.calls.avg_duration_seconds >= 300,
        },
        {
          label: 'Qualified leads',
          value: analytics.leads.by_status.qualified ?? 0,
          sub: 'ready for offer',
          gold: (analytics.leads.by_status.qualified ?? 0) > 0,
        },
        {
          label: 'Converted',
          value: analytics.leads.by_status.converted ?? 0,
          sub: 'closed deals',
          gold: (analytics.leads.by_status.converted ?? 0) > 0,
        },
        {
          label: 'Active workflows',
          value: analytics.workflows.active,
          sub: `${analytics.workflows.completed} completed`,
          highlight: analytics.workflows.active > 0,
        },
        {
          label: 'Workflows done',
          value: analytics.workflows.completed,
          sub: `${analytics.workflows.total} total`,
        },
      ]
    : []

  return (
    <PageContainer title="Dashboard" description="Operational overview">
      <div className="space-y-6 max-w-content">
        {analyticsQuery.isError && <p role="alert" className="text-sm text-destructive">Analytics unavailable. Last successful values, if present, may be stale.</p>}
        {(callsQuery.isError || signalQuery.isError) && <p role="status" className="text-sm text-muted-foreground">Live call or conversation signals unavailable.</p>}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <SophiaStatusWidget activeCall={activeCall} />
          </div>
          <div className="lg:col-span-2">
            {analytics ? (
              <KPIGrid tiles={kpiTiles.slice(0, 4)} cols={2} />
            ) : analyticsQuery.isError ? <p>Analytics could not be loaded.</p> : (
              <div className="grid grid-cols-2 gap-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-24 rounded-lg border bg-card animate-pulse" />
                ))}
              </div>
            )}
          </div>
        </div>

        {analytics && (
          <KPIGrid tiles={kpiTiles.slice(4)} cols={4} />
        )}
      </div>
              <SocialWidget />
        </PageContainer>
  )
}
