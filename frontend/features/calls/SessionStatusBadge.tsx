import { Badge } from '@/components/ui/badge'
import type { CallSessionStatus } from '@/types/call'

const VARIANT: Record<CallSessionStatus, string> = {
  waiting:   'pending',
  active:    'active',
  completed: 'completed',
  failed:    'failed',
}

const LABEL: Record<CallSessionStatus, string> = {
  waiting:   'Waiting',
  active:    'Live',
  completed: 'Completed',
  failed:    'Failed',
}

export function SessionStatusBadge({ status }: { status: CallSessionStatus }) {
  return (
    <Badge variant={VARIANT[status] as Parameters<typeof Badge>[0]['variant']}>
      {LABEL[status]}
    </Badge>
  )
}
