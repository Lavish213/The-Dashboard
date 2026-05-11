'use client'

import { useRealtimeStore } from '@/stores/realtime.store'
import { useWebSocketStore } from '@/stores/websocket.store'
import { ConnectionStatusBadge } from './ConnectionStatusBadge'

export function RealtimeMonitor() {
  const status = useWebSocketStore((s) => s.status)
  const connectionId = useWebSocketStore((s) => s.connectionId)
  const lastError = useWebSocketStore((s) => s.lastError)
  const subscribedChannels = useRealtimeStore((s) => s.subscribedChannels)
  const eventCount = useRealtimeStore((s) => s.eventCount)
  const lastEventAt = useRealtimeStore((s) => s.lastEventAt)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <ConnectionStatusBadge status={status} />
        {connectionId && (
          <span className="font-mono text-xs text-muted-foreground">
            {connectionId}
          </span>
        )}
      </div>

      {lastError && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {lastError}
        </p>
      )}

      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Stat label="Events received" value={String(eventCount)} />
        <Stat
          label="Last event"
          value={lastEventAt ? new Date(lastEventAt).toLocaleTimeString() : '—'}
        />
        <Stat
          label="Subscribed channels"
          value={String(subscribedChannels.size)}
        />
      </dl>

      {subscribedChannels.size > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Channels
          </p>
          <ul className="flex flex-wrap gap-1.5">
            {[...subscribedChannels].map((ch) => (
              <li
                key={ch}
                className="rounded-md bg-muted px-2 py-0.5 font-mono text-xs"
              >
                {ch}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-xl font-semibold tabular-nums">{value}</dd>
    </div>
  )
}
