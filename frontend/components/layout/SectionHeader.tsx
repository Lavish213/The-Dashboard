import * as React from 'react'
import { cn } from '@/lib/utils'

interface SectionHeaderProps {
  title: string
  description?: string
  /** Right slot: actions, buttons */
  actions?: React.ReactNode
  /** Divider below */
  divider?: boolean
  className?: string
}

export function SectionHeader({
  title,
  description,
  actions,
  divider = true,
  className,
}: SectionHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-4',
        divider && 'border-b border-border pb-3',
        className
      )}
    >
      <div className="space-y-0.5 min-w-0">
        <h2 className="text-sm font-semibold leading-none text-foreground truncate">{title}</h2>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && (
        <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>
      )}
    </div>
  )
}
