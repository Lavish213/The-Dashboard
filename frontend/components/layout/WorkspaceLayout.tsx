'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface WorkspaceLayoutProps {
  /** Full-height split workspace with optional right panel */
  children: React.ReactNode
  /** Right panel (detail view, inspector, etc.) */
  panel?: React.ReactNode
  /** Panel width */
  panelWidth?: string
  /** Show panel */
  panelOpen?: boolean
  className?: string
}

/**
 * WorkspaceLayout — secondary content area layout for split workspace views.
 * Master list on left, detail/inspector panel on right.
 * Phase 1: static layout. Animated panel open/close in Phase 2.
 */
export function WorkspaceLayout({
  children,
  panel,
  panelWidth = '420px',
  panelOpen = false,
  className,
}: WorkspaceLayoutProps) {
  return (
    <div className={cn('flex h-full w-full overflow-hidden', className)}>
      {/* Main content */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {children}
      </div>

      {/* Right panel */}
      {panel && panelOpen && (
        <>
          <div className="w-px flex-shrink-0 bg-border" role="separator" aria-orientation="vertical" />
          <aside
            className="flex-shrink-0 overflow-auto"
            style={{ width: panelWidth }}
            aria-label="Detail panel"
          >
            {panel}
          </aside>
        </>
      )}
    </div>
  )
}
