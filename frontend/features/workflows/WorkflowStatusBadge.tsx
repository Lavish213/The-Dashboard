import { Badge } from '@/components/ui/badge'
import type { WorkflowStatus } from '@/types/workflow'

const VARIANT: Record<WorkflowStatus, string> = {
  pending:   'pending',
  active:    'active',
  paused:    'paused',
  completed: 'completed',
  failed:    'failed',
  cancelled: 'outline',
}

const LABEL: Record<WorkflowStatus, string> = {
  pending:   'Pending',
  active:    'Active',
  paused:    'Paused',
  completed: 'Completed',
  failed:    'Failed',
  cancelled: 'Cancelled',
}

export function WorkflowStatusBadge({ status }: { status: WorkflowStatus }) {
  return (
    <Badge variant={VARIANT[status] as Parameters<typeof Badge>[0]['variant']}>
      {LABEL[status]}
    </Badge>
  )
}
