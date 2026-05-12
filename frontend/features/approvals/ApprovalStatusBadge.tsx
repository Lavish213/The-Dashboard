import { Badge } from '@/components/ui/badge'
import type { ApprovalStatus } from '@/types/approval'

const VARIANT: Record<ApprovalStatus, string> = {
  pending:   'pending',
  approved:  'active',
  rejected:  'failed',
  expired:   'outline',
  escalated: 'paused',
}

const LABEL: Record<ApprovalStatus, string> = {
  pending:   'Pending',
  approved:  'Approved',
  rejected:  'Rejected',
  expired:   'Expired',
  escalated: 'Escalated',
}

export function ApprovalStatusBadge({ status }: { status: ApprovalStatus }) {
  return (
    <Badge variant={VARIANT[status] as Parameters<typeof Badge>[0]['variant']}>
      {LABEL[status]}
    </Badge>
  )
}
