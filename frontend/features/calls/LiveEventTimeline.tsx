'use client'

/**
 * LiveEventTimeline — incremental, virtualization-safe event list.
 *
 * Merges historical (paginated) events with realtime stream events.
 * Deduplicates by sequence number.
 * Trims to MAX_EVENTS to prevent unbounded DOM growth.
 * Never reloads full history on reconnect — only fetches missed sequences.
 */

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { CallEvent } from '@/types/call'
import { useCallEvents } from './useCallSession'
import { useCallStream } from './useCallSession'

const MAX_EVENTS = 300

const EVENT_LABEL: Record<string, string> = {
  'call.session_created':          'Session created',
  'call.session_started':          'Session started',
  'call.session_completed':        'Session completed',
  'call.session_failed':           'Session failed',
  'call.participant_joined':       'Participant joined',
  'call.participant_left':         'Participant left',
  'call.participant_reconnected':  'Participant reconnected',
  'call.participant_dropped':      'Participant dropped',
}

interface Props {
  sessionId: string
}

function EventRow({ event }: { event: CallEvent }) {
  const label = EVENT_LABEL[event.event_type] ?? event.event_type
  return (
    <div className="flex items-baseline gap-3 py-1.5 border-b last:border-0">
      <span className="shrink-0 text-xs font-mono text-muted-foreground w-6 text-right">
        {event.sequence}
      </span>
      <span className="text-sm">{label}</span>
      <span className="ml-auto shrink-0 text-xs text-muted-foreground">
        {new Date(event.created_at).toLocaleTimeString()}
      </span>
    </div>
  )
}

export function LiveEventTimeline({ sessionId }: Props) {
  const [page, setPage] = useState(1)
  const { data: historyPage } = useCallEvents(sessionId, page)
  const { streamEvents } = useCallStream(sessionId)

  const historical = historyPage?.items ?? []

  // Merge + deduplicate by sequence, sort ascending, trim
  const allEvents = (() => {
    const seenSeq = new Set<number>()
    const merged: CallEvent[] = []
    for (const e of [...historical, ...streamEvents]) {
      if (!seenSeq.has(e.sequence)) {
        seenSeq.add(e.sequence)
        merged.push(e)
      }
    }
    merged.sort((a, b) => a.sequence - b.sequence)
    return merged.slice(-MAX_EVENTS)
  })()

  const totalPages = historyPage?.total_pages ?? 1

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm font-medium">
        <span>Event Timeline</span>
        <span className="text-xs text-muted-foreground">{allEvents.length} events</span>
      </div>

      <div className="rounded-md border px-3 py-2 max-h-80 overflow-y-auto">
        {allEvents.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-xs text-muted-foreground">
            No events yet
          </div>
        ) : (
          allEvents.map((e) => <EventRow key={`${e.sequence}-${e.id}`} event={e} />)
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Earlier
          </Button>
          <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Later
          </Button>
        </div>
      )}
    </div>
  )
}
