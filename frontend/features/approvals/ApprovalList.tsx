'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { ApprovalType } from '@/types/approval'
import { usePendingApprovals, useApprovalStream } from './useApprovals'
import { ApprovalStatusBadge } from './ApprovalStatusBadge'

const PAGE_SIZE = 20

interface Props {
  onSelect?: (approvalId: string) => void
}

export function ApprovalList({ onSelect }: Props) {
  const [page, setPage] = useState(1)
  const [filterType, setFilterType] = useState<ApprovalType | undefined>()

  // Realtime subscription — invalidates query on WS events
  useApprovalStream()

  const { data, isLoading, error } = usePendingApprovals(page, PAGE_SIZE, filterType)

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        Loading approvals…
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive p-4 text-sm text-destructive">
        Failed to load approvals: {String(error)}
      </div>
    )
  }

  const { items = [], total_pages = 1 } = data ?? {}

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span>Pending Approvals</span>
          <span className="text-xs font-normal text-muted-foreground">
            {data?.total ?? 0} total
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent className="p-0">
        {items.length === 0 ? (
          <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
            No pending approvals
          </div>
        ) : (
          <ul className="divide-y">
            {items.map((approval) => (
              <li
                key={approval.id}
                className="flex cursor-pointer items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors"
                onClick={() => onSelect?.(approval.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && onSelect?.(approval.id)}
              >
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-sm font-medium truncate capitalize">
                    {approval.approval_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-muted-foreground font-mono">
                    {approval.workflow_id.slice(0, 8)}…
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  <span className="text-xs text-muted-foreground capitalize">
                    {approval.risk_level}
                  </span>
                  <ApprovalStatusBadge status={approval.approval_status} />
                </div>
              </li>
            ))}
          </ul>
        )}

        {total_pages > 1 && (
          <div className="flex items-center justify-between border-t px-4 py-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="text-xs text-muted-foreground">
              {page} / {total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
