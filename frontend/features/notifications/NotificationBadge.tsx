'use client'

import { Badge } from '@/components/ui/badge'
import { useUnreadCount } from './useNotifications'

interface NotificationBadgeProps {
  userId: string
}

export function NotificationBadge({ userId }: NotificationBadgeProps) {
  const { data } = useUnreadCount(userId)

  if (!data || data.count === 0) return null

  return (
    <Badge variant="solid-destructive" className="h-5 min-w-5 px-1 text-xs">
      {data.count > 99 ? '99+' : data.count}
    </Badge>
  )
}
