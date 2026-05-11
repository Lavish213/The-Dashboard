'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface SplitPaneProps extends React.HTMLAttributes<HTMLDivElement> {
  direction?: 'horizontal' | 'vertical'
  /** CSS value for first pane size (default '50%') */
  firstSize?: string
  /** Whether first pane has a fixed size (default true) */
  firstFixed?: boolean
}

/**
 * SplitPane — operational split-panel layout primitive
 * Phase 0 shell: static layout only. Resize logic added in Phase 2.
 */
export function SplitPane({
  direction = 'horizontal',
  firstSize = '50%',
  firstFixed = false,
  className,
  children,
  ...props
}: SplitPaneProps) {
  const childArray = React.Children.toArray(children)
  const first  = childArray[0]
  const second = childArray[1]

  if (direction === 'horizontal') {
    return (
      <div
        className={cn('flex h-full w-full overflow-hidden', className)}
        {...props}
      >
        <div
          className={cn('flex-shrink-0 overflow-auto', !firstFixed && 'flex-1')}
          style={firstFixed ? { width: firstSize } : undefined}
        >
          {first}
        </div>
        <div className="w-px shrink-0 bg-border" role="separator" aria-orientation="vertical" />
        <div className="min-w-0 flex-1 overflow-auto">{second}</div>
      </div>
    )
  }

  return (
    <div
      className={cn('flex h-full w-full flex-col overflow-hidden', className)}
      {...props}
    >
      <div
        className={cn('flex-shrink-0 overflow-auto', !firstFixed && 'flex-1')}
        style={firstFixed ? { height: firstSize } : undefined}
      >
        {first}
      </div>
      <div className="h-px shrink-0 bg-border" role="separator" aria-orientation="horizontal" />
      <div className="min-h-0 flex-1 overflow-auto">{second}</div>
    </div>
  )
}

/** Full-height panel with optional header */
export function Panel({
  className,
  header,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { header?: React.ReactNode }) {
  return (
    <div className={cn('flex h-full flex-col', className)} {...props}>
      {header && (
        <div className="flex-shrink-0 border-b border-border px-4 py-2">{header}</div>
      )}
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  )
}
