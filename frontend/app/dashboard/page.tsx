'use client'

import { useEffect, useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { KPIGrid } from '@/components/dashboard/KPIGrid'
import { SophiaStatusWidget } from '@/components/dashboard/SophiaStatusWidget'
import { apiFetch } from '@/services/api'
import { useSophiaStore } from '@/stores/sophia.store'
import { getSignals } from '@/services/sophia'

interface Analytics {
  leads: { total: number; by_status: Record<string, number> }
  calls: { total: number; completed: number; contact_rate: number; avg_duration_seconds: number }
  workflows: { total: number; active: number; completed: number }
}

interface ActiveCall {
  session_id: string
  caller_name: string | null
  phone: string | null
  duration_seconds: number
}

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [activeCall, setActiveCall] = useState<ActiveCall | null>(null)
  const { signals, setSignals, sessionId, setSessionId } = useSophiaStore()

  useEffect(() => {
    apiFetch<Analytics>('/api/v1/analytics').then(setAnalytics).catch(() => {})

    const id = setInterval(() => {
      apiFetch<Analytics>('/api/v1/analytics').then(setAnalytics).catch(() => {})
    }, 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    async function pollActiveCall() {
      try {
        const data = await apiFetch<{ items: any[]; total: number }>(
          '/api/v1/calls?call_status=connected&page_size=1'
        )
        if (data.items.length > 0) {
          const call = data.items[0]
          setActiveCall({
            session_id: call.id,
            caller_name: null,
            phone: null,
            duration_seconds: call.duration_seconds ?? 0,
          })
          setSessionId(call.id)
        } else {
          setActiveCall(null)
        }
      } catch {}
    }
    pollActiveCall()
    const id = setInterval(pollActiveCall, 5_000)
    return () => clearInterval(id)
  }, [setSessionId])

  useEffect(() => {
    if (!sessionId) return
    async function poll() {
      try {
        const s = await getSignals(sessionId!)
        setSignals(s)
      } catch {}
    }
    poll()
    const id = setInterval(poll, 10_000)
    return () => clearInterval(id)
  }, [sessionId, setSignals])

  const kpiTiles = analytics
    ? [
        {
          label: 'Total leads',
          value: analytics.leads.total,
          sub: `${analytics.leads.by_status.new ?? 0} new`,
          trend: [2, 4, 3, 6, 5, 8, analytics.leads.total],
          highlight: false,
        },
        {
          label: 'Total calls',
          value: analytics.calls.total,
          sub: `${analytics.calls.completed} completed`,
          trend: [1, 3, 2, 5, 4, 7, analytics.calls.total],
        },
        {
          label: 'Contact rate',
          value: `${analytics.calls.contact_rate}%`,
          sub: 'calls answered',
          trend: [40, 45, 52, 48, 55, 58, analytics.calls.contact_rate],
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
          trend: [0, 1, 1, 2, 2, 3, analytics.leads.by_status.qualified ?? 0],
          gold: (analytics.leads.by_status.qualified ?? 0) > 0,
        },
        {
          label: 'Converted',
          value: analytics.leads.by_status.converted ?? 0,
          sub: 'closed deals',
          trend: [0, 0, 1, 1, 2, 3, analytics.leads.by_status.converted ?? 0],
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
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <SophiaStatusWidget activeCall={activeCall} />
          </div>
          <div className="lg:col-span-2">
            {analytics ? (
              <KPIGrid tiles={kpiTiles.slice(0, 4)} cols={2} />
            ) : (
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
    </PageContainer>
  )
}