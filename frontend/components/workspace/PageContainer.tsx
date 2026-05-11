import * as React from 'react'
import { cn } from '@/lib/utils'

interface PageContainerProps {
  children: React.ReactNode
  /** Page title — rendered as h1, used by screen readers */
  title?: string
  /** Subtitle below title */
  description?: string
  /** Slot for page-level actions (buttons, filters) */
  actions?: React.ReactNode
  /** Constrain max width */
  constrain?: boolean
  /** Extra padding on bottom for mobile bottom nav */
  mobilePadding?: boolean
  className?: string
}

/**
 * PageContainer — standard page-level wrapper.
 * Provides consistent header/title structure, padding, and scroll context.
 */
export function PageContainer({
  children,
  title,
  description,
  actions,
  constrain = false,
  mobilePadding = true,
  className,
}: PageContainerProps) {
  return (
    <div
      className={cn(
        'flex h-full flex-col',
        mobilePadding && 'pb-16 md:pb-0', // space for bottom nav on mobile
        className
      )}
    >
      {(title || actions) && (
        <div className="flex-shrink-0 border-b border-border px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5 min-w-0">
              {title && (
                <h1 className="text-base font-semibold text-foreground leading-none">
                  {title}
                </h1>
              )}
              {description && (
                <p className="text-xs text-muted-foreground">{description}</p>
              )}
            </div>
            {actions && (
              <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>
            )}
          </div>
        </div>
      )}

      <div
        className={cn(
          'flex-1 overflow-auto px-6 py-4',
          constrain && 'mx-auto w-full max-w-7xl'
        )}
      >
        {children}
      </div>
    </div>
  )
}
