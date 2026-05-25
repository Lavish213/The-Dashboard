'use client'

import { ModeIndicator } from '@/components/sophia/ModeIndicator'
import { DealHeatGauge } from '@/components/sophia/DealHeatGauge'
import { TrustScore } from '@/components/sophia/TrustScore'
import { useSophiaStore } from '@/stores/sophia.store'

interface ActiveCall {
  session_id: string
  caller_name: string | null
  phone: string | null
  duration_seconds: number
}

interface SophiaStatusWidgetProps {
  activeCall?: ActiveCall | null
}

function formatDuration(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

export function SophiaStatusWidget({ activeCall }: SophiaStatusWidgetProps) {
  const { signals, sessionId } = useSophiaStore()

  return (
    <div className="rounded-lg border bg-card shadow-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-foreground font-display">Sophia</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {activeCall
              ? `Call in progress · ${formatDuration(activeCall.duration_seconds)}`
              : sessionId
              ? `Session ${sessionId.slice(0, 8)}…`
              : 'Idle — waiting for calls'}
          </p>
        </div>
        <ModeIndicator />
      </div>

      {activeCall && (
        <div className="flex items-center gap-3 rounded-md border border-teal-500/20 bg-teal-500/5 px-3 py-2">
          <div className="h-2 w-2 rounded-full bg-teal-400 animate-pulse-teal flex-shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">
              {activeCall.caller_name ?? 'Unknown caller'}
            </p>
            <p className="text-xs text-muted-foreground">{activeCall.phone ?? '—'}</p>
          </div>
          <p className="text-sm font-semibold tabular-nums text-teal-400 font-mono flex-shrink-0">
            {formatDuration(activeCall.duration_seconds)}
          </p>
        </div>
      )}

      {signals && (
        <div className="space-y-2 pt-1 border-t border-border">
          <DealHeatGauge value={signals.deal_heat} />
          <TrustScore value={signals.trust_score} />
        </div>
      )}

      {!signals && !activeCall && (
        <div className="text-center py-2">
          <p className="text-xs text-muted-foreground">No active signals</p>
        </div>
      )}
    </div>
  )
}