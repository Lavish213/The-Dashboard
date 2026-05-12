'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuditTimeline } from './useAuditTimeline'
import type { AuditFilters, AuditLogEntry } from './api'

function actorVariant(
  actorType: AuditLogEntry['actor_type']
): 'default' | 'secondary' | 'outline' {
  switch (actorType) {
    case 'user':
      return 'default'
    case 'ai':
      return 'secondary'
    case 'system':
      return 'outline'
  }
}

export function AuditTimelineViewer() {
  const [page, setPage] = useState(1)
  const pageSize = 20

  const [targetTypeInput, setTargetTypeInput] = useState('')
  const [actionInput, setActionInput] = useState('')

  const [filters, setFilters] = useState<AuditFilters>({})

  const { data, isLoading, refetch } = useAuditTimeline(filters, page, pageSize)

  function applyFilters() {
    const next: AuditFilters = {}
    if (targetTypeInput.trim()) next.target_type = targetTypeInput.trim()
    if (actionInput.trim()) next.action = actionInput.trim()
    setFilters(next)
    setPage(1)
  }

  function clearFilters() {
    setTargetTypeInput('')
    setActionInput('')
    setFilters({})
    setPage(1)
  }

  return (
    <Card>
      <CardHeader className="space-y-0 pb-2">
        <CardTitle className="text-base font-semibold">Audit Timeline</CardTitle>

        <div className="flex flex-wrap items-end gap-2 pt-2">
          <input
            type="text"
            placeholder="Target type"
            value={targetTypeInput}
            onChange={(e) => setTargetTypeInput(e.target.value)}
            className="h-8 rounded-md border bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <input
            type="text"
            placeholder="Action"
            value={actionInput}
            onChange={(e) => setActionInput(e.target.value)}
            className="h-8 rounded-md border bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <Button size="sm" onClick={applyFilters}>
            Filter
          </Button>
          <Button variant="outline" size="sm" onClick={clearFilters}>
            Clear
          </Button>
          <Button variant="ghost" size="sm" onClick={() => void refetch()}>
            Refresh
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}

        {!isLoading && data?.items.length === 0 && (
          <p className="text-sm text-muted-foreground">No audit entries found.</p>
        )}

        {!isLoading && data && data.items.length > 0 && (
          <div className="space-y-1">
            {data.items.map((entry) => (
              <div
                key={entry.id}
                className="grid grid-cols-[140px_1fr] gap-x-3 rounded-md border px-3 py-2 text-sm"
              >
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">
                    {new Date(entry.created_at).toLocaleString()}
                  </p>
                  <Badge variant={actorVariant(entry.actor_type)} className="text-xs">
                    {entry.actor_type}
                  </Badge>
                </div>
                <div className="min-w-0 space-y-0.5">
                  <p className="font-medium">{entry.action}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {entry.target_type}
                    {entry.target_id ? `:${entry.target_id}` : ''}
                  </p>
                </div>
              </div>
            ))}

            {data.total_pages > 1 && (
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
                  Page {page} of {data.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={page === data.total_pages}
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
