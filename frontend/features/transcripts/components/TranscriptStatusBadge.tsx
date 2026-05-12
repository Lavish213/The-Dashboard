import { Badge } from '@/components/ui/badge'
import type { TranscriptStatus } from '@/types/transcript'

const VARIANT: Record<TranscriptStatus, string> = {
  created:   'outline',
  active:    'active',
  paused:    'paused',
  completed: 'completed',
  failed:    'failed',
  archived:  'outline',
}

const LABEL: Record<TranscriptStatus, string> = {
  created:   'Created',
  active:    'Active',
  paused:    'Paused',
  completed: 'Completed',
  failed:    'Failed',
  archived:  'Archived',
}

export function TranscriptStatusBadge({ status }: { status: TranscriptStatus }) {
  return (
    <Badge variant={VARIANT[status] as Parameters<typeof Badge>[0]['variant']}>
      {LABEL[status]}
    </Badge>
  )
}
