'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useApproval, useResolveApproval } from './useApprovals'
import { ApprovalStatusBadge } from './ApprovalStatusBadge'

interface Props {
  approvalId: string
  resolvedBy: string  // caller passes current user id
}

export function ApprovalDetail({ approvalId, resolvedBy }: Props) {
  const { data: approval, isLoading, error } = useApproval(approvalId)
  const resolve = useResolveApproval()

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    )
  }

  if (error || !approval) {
    return (
      <div className="rounded-md border border-destructive p-4 text-sm text-destructive">
        Failed to load approval
      </div>
    )
  }

  const isPending = approval.approval_status === 'pending'

  const handleResolve = (approved: boolean) => {
    resolve.mutate({
      id: approvalId,
      body: {
        approval_status: approved ? 'approved' : 'rejected',
        resolved_by: resolvedBy,
      },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="capitalize">{approval.approval_type.replace(/_/g, ' ')}</span>
          <ApprovalStatusBadge status={approval.approval_status} />
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        <Row label="Workflow" value={approval.workflow_id} mono />
        <Row label="Risk" value={<span className="capitalize">{approval.risk_level}</span>} />
        <Row label="Requested by" value={approval.requested_by ?? '—'} mono />
        {approval.resolved_by && (
          <Row label="Resolved by" value={approval.resolved_by} mono />
        )}
        {approval.expires_at && (
          <Row
            label="Expires"
            value={new Date(approval.expires_at).toLocaleString()}
          />
        )}
        {approval.resolution_notes && (
          <Row label="Notes" value={approval.resolution_notes} />
        )}
        <Row label="Created" value={new Date(approval.created_at).toLocaleString()} />

        {isPending && (
          <div className="flex gap-2 pt-2">
            <Button
              size="sm"
              onClick={() => handleResolve(true)}
              disabled={resolve.isPending}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => handleResolve(false)}
              disabled={resolve.isPending}
            >
              Reject
            </Button>
          </div>
        )}

        {resolve.isError && (
          <p className="text-xs text-destructive">{String(resolve.error)}</p>
        )}
      </CardContent>
    </Card>
  )
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className={`text-right break-all ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  )
}
