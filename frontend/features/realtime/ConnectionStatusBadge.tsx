'use client'

import { cn } from '@/lib/utils'
import type { ConnectionStatus } from '@/types/websocket'

interface Props {
  status: ConnectionStatus
}

const STATUS_STYLES: Record<ConnectionStatus, string> = {
  connected: 'bg-green-500/20 text-green-700 dark:text-green-400',
  connecting: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-400',
  reconnecting: 'bg-orange-500/20 text-orange-700 dark:text-orange-400',
  disconnected: 'bg-gray-500/20 text-gray-600 dark:text-gray-400',
  error: 'bg-red-500/20 text-red-700 dark:text-red-400',
}

const STATUS_DOT: Record<ConnectionStatus, string> = {
  connected: 'bg-green-500 animate-pulse',
  connecting: 'bg-yellow-500 animate-pulse',
  reconnecting: 'bg-orange-500 animate-pulse',
  disconnected: 'bg-gray-400',
  error: 'bg-red-500',
}

export function ConnectionStatusBadge({ status }: Props) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        STATUS_STYLES[status],
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', STATUS_DOT[status])} />
      {status}
    </span>
  )
}
