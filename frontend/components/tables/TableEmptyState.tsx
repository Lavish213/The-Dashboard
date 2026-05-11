import * as React from 'react'
import { cn } from '@/lib/utils'
import { InboxIcon } from 'lucide-react'

interface TableEmptyStateProps {
  title?: string
  description?: string
  action?: React.ReactNode
  icon?: React.ReactNode
  className?: string
}

export function TableEmptyState({
  title = 'No results',
  description = 'No data matches your current filters.',
  action,
  icon,
  className,
}: TableEmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 py-16 text-center',
        className
      )}
      role="status"
      aria-label={title}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
        {icon ?? <InboxIcon className="h-6 w-6" />}
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  )
}
