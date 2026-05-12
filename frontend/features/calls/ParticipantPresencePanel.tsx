'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCallPresence } from './useCallSession'
import { ConnectionHealthBadge } from './ConnectionHealthBadge'

interface Props {
  sessionId: string
}

export function ParticipantPresencePanel({ sessionId }: Props) {
  const { data: presence = [], isLoading } = useCallPresence(sessionId)

  if (isLoading) {
    return (
      <div className="flex h-16 items-center justify-center text-sm text-muted-foreground">
        Loading presence…
      </div>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-sm">
          <span>Participants</span>
          <span className="text-xs font-normal text-muted-foreground">
            {presence.filter((p) => p.participant_status === 'joined').length} online
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {presence.length === 0 ? (
          <div className="flex h-12 items-center justify-center text-xs text-muted-foreground">
            No participants
          </div>
        ) : (
          <ul className="divide-y">
            {presence.map((p) => (
              <li key={p.participant_id} className="flex items-center justify-between px-4 py-2">
                <span className="font-mono text-xs text-muted-foreground">
                  {p.participant_id.slice(0, 8)}…
                </span>
                <ConnectionHealthBadge status={p.participant_status} isStale={p.is_stale} />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
