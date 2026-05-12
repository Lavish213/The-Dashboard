'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useActiveSessions,
  useActiveSessionCount,
  useDisconnectSession,
  useCleanupStale,
} from './useOperatorSessions'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

export function OperatorSessionsPanel() {
  const [page, setPage] = useState(1)
  const pageSize = 20

  const { data: countData } = useActiveSessionCount()
  const { data: sessions, isLoading } = useActiveSessions(page, pageSize)
  const disconnect = useDisconnectSession()
  const cleanup = useCleanupStale()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-semibold">
          Operator Sessions
          {countData != null && (
            <Badge variant="secondary" className="ml-2">
              {countData.count} active
            </Badge>
          )}
        </CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={() => cleanup.mutate(undefined)}
          disabled={cleanup.isPending}
        >
          {cleanup.isPending ? 'Cleaning…' : 'Cleanup Stale'}
        </Button>
      </CardHeader>

      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}

        {!isLoading && sessions?.items.length === 0 && (
          <p className="text-sm text-muted-foreground">No active sessions.</p>
        )}

        {!isLoading && sessions && sessions.items.length > 0 && (
          <div className="space-y-2">
            {sessions.items.map((session) => (
              <div
                key={session.id}
                className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
              >
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className="truncate font-mono text-xs text-muted-foreground">
                    {session.socket_id}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Connected: {formatDate(session.connected_at)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Heartbeat: {formatDate(session.last_heartbeat_at)}
                  </p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  className="ml-4 shrink-0"
                  onClick={() => disconnect.mutate(session.id)}
                  disabled={disconnect.isPending}
                >
                  Disconnect
                </Button>
              </div>
            ))}

            {sessions.total_pages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <span className="text-xs text-muted-foreground">
                  Page {page} of {sessions.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(sessions.total_pages, p + 1))}
                  disabled={page === sessions.total_pages}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
