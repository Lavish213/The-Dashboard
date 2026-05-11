'use client'

import * as React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Clock } from 'lucide-react'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired'

export interface ApprovalCardProps {
  id: string
  title: string
  description?: string
  requestedBy?: string
  requestedAt?: string
  expiresAt?: string
  status: ApprovalStatus
  /** Metadata key-value pairs */
  meta?: Record<string, string>
  onApprove?: (id: string) => void
  onReject?: (id: string) => void
  loading?: boolean
  className?: string
}

const statusBadge: Record<ApprovalStatus, string> = {
  pending: 'pending',
  approved: 'active',
  rejected: 'failed',
  expired: 'secondary',
}

export function ApprovalCard({
  id,
  title,
  description,
  requestedBy,
  requestedAt,
  expiresAt,
  status,
  meta,
  onApprove,
  onReject,
  loading = false,
  className,
}: ApprovalCardProps) {
  const isPending = status === 'pending'

  return (
    <Card
      variant={status === 'rejected' ? 'alert' : status === 'approved' ? 'success' : 'default'}
      className={className}
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-0.5 min-w-0">
            <p className="text-sm font-medium leading-none truncate">{title}</p>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
          <Badge variant={statusBadge[status] as Parameters<typeof Badge>[0]['variant']} className="flex-shrink-0">
            {status}
          </Badge>
        </div>

        {/* Meta rows */}
        {meta && Object.keys(meta).length > 0 && (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
            {Object.entries(meta).map(([k, v]) => (
              <div key={k}>
                <dt className="text-[10px] text-muted-foreground uppercase tracking-wider">{k}</dt>
                <dd className="text-xs font-medium truncate">{v}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="flex items-center justify-between gap-2">
          <div className="space-y-0.5">
            {requestedBy && (
              <p className="text-[10px] text-muted-foreground">
                By <span className="font-medium">{requestedBy}</span>
                {requestedAt && <span> · {requestedAt}</span>}
              </p>
            )}
            {expiresAt && isPending && (
              <p className="flex items-center gap-1 text-[10px] text-warning">
                <Clock className="h-3 w-3" />
                Expires {expiresAt}
              </p>
            )}
          </div>

          {isPending && (onApprove || onReject) && (
            <div className="flex items-center gap-1.5">
              {onReject && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onReject(id)}
                  disabled={loading}
                  className="h-7 px-3 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
                >
                  Reject
                </Button>
              )}
              {onApprove && (
                <Button
                  size="sm"
                  onClick={() => onApprove(id)}
                  disabled={loading}
                  className="h-7 px-3 text-xs"
                >
                  Approve
                </Button>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
