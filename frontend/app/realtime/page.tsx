'use client'

import { useEffect, useRef, useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { ModeIndicator } from '@/components/sophia/ModeIndicator'
import { DealHeatGauge } from '@/components/sophia/DealHeatGauge'
import { TrustScore } from '@/components/sophia/TrustScore'
import { ConfidenceMeter } from '@/components/sophia/ConfidenceMeter'
import { TakeoverButton } from '@/components/sophia/TakeoverButton'
import { ContextPacketPanel } from '@/components/sophia/ContextPacketPanel'
import { useSophiaStore } from '@/stores/sophia.store'
import { getSignals } from '@/services/sophia'
import { apiFetch } from '@/services/api'

interface ActiveCall {
  session_id: string
  turn_id: string
  caller_name: string | null
  phone: string | null
  duration_seconds: number
  status: string
}

interface RecentCall {
  id: string
  caller_name: string | null
  duration_seconds: number
  outcome: string | null
  cost_usd: number | null
  created_at: string
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function OutcomeBadge({ outcome }: { outcome: string }) {
  const map: Record<string, string> = {
    appointment_set: 'bg-green-500/10 text-green-400 border-green-500/20',
    callback: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    no_answer: 'bg-muted text-muted-foreground border-border',
    not_interested: 'bg-red-500/10 text-red-400 border-red-500/20',
    qualified: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
    dead: 'bg-muted text-muted-foreground border-border',
  }
  const cls = map[outcome] ?? 'bg-muted text-muted-foreground border-border'
  return (
    <span className={`rounded border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {outcome.replace(/_/g, ' ')}
    </span>
  )
}

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export default function RealtimePage() {
  const { mode, signals, setSignals, setSessionId, sessionId } = useSophiaStore()
  const [activeCall, setActiveCall] = useState<ActiveCall | null>(null)
  const [recentCalls, setRecentCalls] = useState<RecentCall[]>([])
  const [loading, setLoading] = useState(true)
  const signalInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    async function poll() {
      try {
        const data = await apiFetch<{ active: ActiveCall | null; recent: RecentCall[] }>(
          '/api/v1/realtime/active-call'
        )
        setActiveCall(data.active)
        setRecentCalls(data.recent ?? [])
        if (data.active) {
          setSessionId(data.active.session_id)
        } else {
          setSessionId(null)
        }
      } catch {
      } finally {
        setLoading(false)
      }
    }
    poll()
    const id = setInterval(poll, 5000)
    return () => clearInterval(id)
  }, [setSessionId])

  useEffect(() => {
    if (!sessionId) return
    async function pollSignals() {
      try {
        const s = await getSignals(sessionId!)
        setSignals(s)
      } catch {}
    }
    pollSignals()
    signalInterval.current = setInterval(pollSignals, 5000)
    return () => {
      if (signalInterval.current) clearInterval(signalInterval.current)
    }
  }, [sessionId, setSignals])

  const isHuman = mode === 'human_takeover'

  return (
    <PageContainer
      title="Sophia Live"
      description="Real-time call monitoring and agent health"
    >
      <div className="space-y-6 max-w-2xl">
        <div className="flex items-center justify-between">
          <ModeIndicator />
          {activeCall && (
            <div className="text-xs text-muted-foreground">
              Session: <span className="font-mono text-teal-400">{activeCall.session_id.slice(0, 8)}…</span>
            </div>
          )}
        </div>

        {loading && (
          <div className="rounded-lg border bg-card p-6 animate-pulse h-32" />
        )}

        {!loading && !activeCall && (
          <div className="rounded-lg border bg-card p-10 text-center shadow-card">
            <div className="h-2 w-2 rounded-full bg-muted mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">No active call</p>
            <p className="text-xs text-muted-foreground mt-1">Sophia is idle</p>
          </div>
        )}

        {!loading && activeCall && (
          <div className="rounded-lg border border-teal-500/20 bg-teal-500/5 shadow-card p-4 space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-teal-500/15 border border-teal-500/25 flex items-center justify-center text-sm font-semibold text-teal-400 flex-shrink-0">
                {(activeCall.caller_name ?? '?')[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground">
                  {activeCall.caller_name ?? 'Unknown caller'}
                </p>
                <p className="text-xs text-muted-foreground font-mono">
                  {activeCall.phone ?? activeCall.session_id?.slice(0, 16) ?? '—'}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-xl font-semibold tabular-nums text-teal-400 font-mono">
                  {formatDuration(activeCall.duration_seconds)}
                </p>
                <p className="text-xs text-muted-foreground">duration</p>
              </div>
            </div>

            {signals && !isHuman && (
              <div className="grid gap-3 pt-3 border-t border-teal-500/15">
                <DealHeatGauge value={signals.deal_heat} />
                <TrustScore value={signals.trust_score} />
                <ConfidenceMeter
                  value={signals.confidence_score}
                  handoffRecommended={signals.handoff_recommended}
                />
                {signals.signal_notes.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {signals.signal_notes.map((note, i) => (
                      <span
                        key={i}
                        className="rounded border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                      >
                        {note}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!signals && (
              <div className="pt-3 border-t border-teal-500/15">
                <p className="text-xs text-muted-foreground text-center">
                  Waiting for signal data…
                </p>
              </div>
            )}

            {!isHuman && (
              <div className="pt-2 border-t border-teal-500/15">
                <TakeoverButton
                  turnId={activeCall.turn_id}
                  onSuccess={() => {}}
                />
              </div>
            )}
          </div>
        )}

        {isHuman && <ContextPacketPanel />}

        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Recent calls
          </p>
          {recentCalls.length === 0 && (
            <p className="text-xs text-muted-foreground py-2">No recent calls</p>
          )}
          {recentCalls.map((call) => (
            <div
              key={call.id}
              className="flex items-center gap-3 rounded-lg border bg-card shadow-card px-4 py-3 hover:border-border/80 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground truncate">
                  {call.caller_name ?? 'Unknown caller'}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {call.created_at ? formatDate(call.created_at) : '—'}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {call.outcome && <OutcomeBadge outcome={call.outcome} />}
                <span className="text-xs text-muted-foreground tabular-nums font-mono">
                  {formatDuration(call.duration_seconds ?? 0)}
                </span>
                {call.cost_usd != null && (
                  <span className="text-xs text-muted-foreground">
                    ${call.cost_usd.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </PageContainer>
  )
}