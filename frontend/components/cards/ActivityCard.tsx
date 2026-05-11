import * as React from 'react'
import { Card, CardContent } from '@/components/ui/card'

export interface ActivityItem {
  id: string
  actor: string
  action: string
  target?: string
  timestamp: string
  icon?: React.ReactNode
  meta?: string
}

export interface ActivityCardProps {
  title?: string
  items: ActivityItem[]
  maxItems?: number
  className?: string
}

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      {item.icon ? (
        <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground text-[10px]">
          {item.icon}
        </span>
      ) : (
        <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-muted-foreground/40" />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-xs text-foreground">
          <span className="font-medium">{item.actor}</span>
          {' '}
          <span className="text-muted-foreground">{item.action}</span>
          {item.target && (
            <>
              {' '}
              <span className="font-medium">{item.target}</span>
            </>
          )}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[10px] text-muted-foreground/70">{item.timestamp}</span>
          {item.meta && (
            <span className="text-[10px] text-muted-foreground/50">{item.meta}</span>
          )}
        </div>
      </div>
    </div>
  )
}

export function ActivityCard({
  title = 'Activity',
  items,
  maxItems = 10,
  className,
}: ActivityCardProps) {
  const visible = items.slice(0, maxItems)

  return (
    <Card className={className}>
      {title && (
        <div className="border-b border-border px-4 py-2">
          <p className="text-sm font-medium">{title}</p>
        </div>
      )}
      <CardContent className="p-0">
        {visible.length === 0 ? (
          <p className="px-4 py-6 text-center text-xs text-muted-foreground">
            No recent activity
          </p>
        ) : (
          <div className="divide-y divide-border/50">
            {visible.map((item) => (
              <div key={item.id} className="px-4">
                <ActivityRow item={item} />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
