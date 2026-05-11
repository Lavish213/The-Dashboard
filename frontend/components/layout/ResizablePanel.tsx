'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface ResizablePanelProps {
  defaultSize?: number
  minSize?: number
  maxSize?: number
  direction?: 'horizontal' | 'vertical'
  className?: string
  children: React.ReactNode
}

/**
 * ResizablePanel — Phase 1 static shell.
 * Interactive resize drag handle added in Phase 2.
 * Currently renders fixed-size panel at defaultSize.
 */
export function ResizablePanel({
  defaultSize = 50,
  minSize: _minSize,
  maxSize: _maxSize,
  direction = 'horizontal',
  className,
  children,
}: ResizablePanelProps) {
  const style =
    direction === 'horizontal'
      ? { width: `${defaultSize}%` }
      : { height: `${defaultSize}%` }

  return (
    <div
      className={cn('overflow-auto', className)}
      style={style}
      data-phase2="resize-handle"
    >
      {children}
    </div>
  )
}
