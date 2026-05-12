'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useNotifications,
  useUnreadCount,
  useMarkRead,
  useMarkAllRead,
} from './useNotifications'
import type { NotificationItem } from './api'

function typeLabel(type: NotificationItem['notification_type']): string {
  switch (type) {
    case 'approval_required':
      return 'Approval'
    case 'workflow_update':
      return 'Workflow'
    case 'system_alert':
      return 'System'
    case 'lead_activity':
      return 'Lead'
  }
}

interface NotificationCenterProps {
  userId: string
}

export function NotificationCenter({ userId }: NotificationCenterProps) {
  const [page, setPage] = useState(1)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const pageSize = 20

  const { data: countData } = useUnreadCount(userId)
  const { data: notifications, isLoading } = useNotifications(userId, page, pageSize, unreadOnly)
  const markRead = useMarkRead()
  const markAllRead = useMarkAllRead()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-semibold">
          Notifications
          {countData != null && countData.count > 0 && (
            <Badge variant="solid-destructive" className="ml-2">
              {countData.count}
            </Badge>
          )}
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant={unreadOnly ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setUnreadOnly((v) => !v)
              setPage(1)
            }}
          >
            Unread only
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => markAllRead.mutate(userId)}
            disabled={markAllRead.isPending}
          >
            Mark all read
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}

        {!isLoading && notifications?.items.length === 0 && (
          <p className="text-sm text-muted-foreground">No notifications.</p>
        )}

        {!isLoading && notifications && notifications.items.length > 0 && (
          <div className="space-y-2">
            {notifications.items.map((n) => (
              <div
                key={n.id}
                className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2 text-sm ${
                  n.read_at == null ? 'bg-muted/50' : ''
                }`}
              >
                <div className="min-w-0 flex-1 space-y-0.5">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="shrink-0 text-xs">
                      {typeLabel(n.notification_type)}
                    </Badge>
                    <p className="truncate font-medium">{n.title}</p>
                  </div>
                  <p className="text-xs text-muted-foreground">{n.body}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(n.created_at).toLocaleString()}
                  </p>
                </div>
                {n.read_at == null && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0"
                    onClick={() => markRead.mutate({ id: n.id, userId })}
                    disabled={markRead.isPending}
                  >
                    Mark read
                  </Button>
                )}
              </div>
            ))}

            {notifications.total_pages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <span className="text-xs text-muted-foreground">
                  Page {page} of {notifications.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setPage((p) => Math.min(notifications.total_pages, p + 1))
                  }
                  disabled={page === notifications.total_pages}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
