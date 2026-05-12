'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useHealth, useReadiness, useMetrics } from './useHealth'

function statusVariant(
  value: string | undefined,
  okValues: string[]
): 'active' | 'failed' | 'secondary' {
  if (!value) return 'secondary'
  return okValues.includes(value) ? 'active' : 'failed'
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return `${h}h ${m}m ${s}s`
}

function MetricRow({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="flex items-center justify-between py-0.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value ?? '—'}</span>
    </div>
  )
}

export function RuntimeHealthPanel() {
  const { data: health } = useHealth()
  const { data: ready } = useReadiness()
  const { data: metrics } = useMetrics()

  const wsMetrics = metrics?.websocket as Record<string, number> | undefined
  const sessionMetrics = metrics?.operator_sessions as Record<string, number> | undefined
  const requestMetrics = metrics?.requests as Record<string, number> | undefined

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold">Runtime Health</CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Status badges */}
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Liveness</span>
            <Badge variant={statusVariant(health?.status, ['ok'])}>
              {health?.status ?? '…'}
            </Badge>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Readiness</span>
            <Badge variant={statusVariant(ready?.status, ['ready'])}>
              {ready?.status ?? '…'}
            </Badge>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">DB</span>
            <Badge variant={statusVariant(ready?.db, ['ok', 'connected'])}>
              {ready?.db ?? '…'}
            </Badge>
          </div>
        </div>

        {/* System info */}
        {health && (
          <div>
            <p className="mb-1 text-xs font-medium text-muted-foreground">System</p>
            <MetricRow label="Version" value={health.version} />
            <MetricRow label="Environment" value={health.env} />
          </div>
        )}

        {/* Uptime + key metrics */}
        {metrics && (
          <div>
            <p className="mb-1 text-xs font-medium text-muted-foreground">Metrics</p>
            <MetricRow label="Uptime" value={formatUptime(metrics.uptime_seconds)} />
            {requestMetrics?.total != null && (
              <MetricRow label="Requests total" value={requestMetrics.total} />
            )}
            {wsMetrics?.active_connections != null && (
              <MetricRow label="Active WS connections" value={wsMetrics.active_connections} />
            )}
            {sessionMetrics?.connected != null && (
              <MetricRow label="Sessions connected" value={sessionMetrics.connected} />
            )}
            {sessionMetrics?.expired != null && (
              <MetricRow label="Sessions expired" value={sessionMetrics.expired} />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
