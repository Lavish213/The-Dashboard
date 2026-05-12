import { Badge } from '@/components/ui/badge'
import type { ParticipantStatus } from '@/types/call'

const VARIANT: Record<ParticipantStatus, string> = {
  joined:       'active',
  reconnecting: 'paused',
  dropped:      'failed',
  left:         'outline',
}

const LABEL: Record<ParticipantStatus, string> = {
  joined:       'Online',
  reconnecting: 'Reconnecting',
  dropped:      'Dropped',
  left:         'Left',
}

interface Props {
  status: ParticipantStatus
  isStale?: boolean
}

export function ConnectionHealthBadge({ status, isStale }: Props) {
  const label = isStale ? 'Stale' : LABEL[status]
  const variant = isStale ? 'failed' : VARIANT[status]
  return (
    <Badge variant={variant as Parameters<typeof Badge>[0]['variant']}>
      {label}
    </Badge>
  )
}
