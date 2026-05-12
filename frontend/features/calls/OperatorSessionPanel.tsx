'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useCallSession, useCompleteSession, useFailSession } from './useCallSession'
import { SessionStatusBadge } from './SessionStatusBadge'
import { ParticipantPresencePanel } from './ParticipantPresencePanel'
import { LiveEventTimeline } from './LiveEventTimeline'

interface Props {
  sessionId: string
}

export function OperatorSessionPanel({ sessionId }: Props) {
  const { data: session, isLoading, error } = useCallSession(sessionId)
  const complete = useCompleteSession()
  const fail = useFailSession()

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        Loading session…
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="rounded-md border border-destructive p-4 text-sm text-destructive">
        Failed to load session
      </div>
    )
  }

  const isTerminal = session.session_status === 'completed' || session.session_status === 'failed'

  return (
    <div className="space-y-4">
      {/* Session header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base">
            <span className="font-mono text-sm">{sessionId.slice(0, 8)}…</span>
            <SessionStatusBadge status={session.session_status} />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {session.started_at && (
            <Row label="Started" value={new Date(session.started_at).toLocaleTimeString()} />
          )}
          {session.ended_at && (
            <Row label="Ended" value={new Date(session.ended_at).toLocaleTimeString()} />
          )}
          {session.call_id && (
            <Row label="Call" value={session.call_id} mono />
          )}

          {!isTerminal && (
            <div className="flex gap-2 pt-2">
              <Button
                size="sm"
                onClick={() => complete.mutate(sessionId)}
                disabled={complete.isPending}
              >
                Complete
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => fail.mutate({ sessionId, reason: 'operator_ended' })}
                disabled={fail.isPending}
              >
                Fail
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Presence */}
      <ParticipantPresencePanel sessionId={sessionId} />

      {/* Events */}
      <LiveEventTimeline sessionId={sessionId} />
    </div>
  )
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className={`text-right break-all ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  )
}
