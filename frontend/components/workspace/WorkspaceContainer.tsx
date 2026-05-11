'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/stores/ui.store'

interface WorkspaceContainerProps {
  children: React.ReactNode
  /** Right panel content (detail view, inspector) */
  panel?: React.ReactNode
  /** Override panel open state */
  panelOpen?: boolean
  className?: string
}

/**
 * WorkspaceContainer — split-pane workspace with optional right panel.
 * Reads panel state from UIStore; panel width is persisted.
 * Phase 2: static layout. Animated resize in Phase 3+.
 */
export function WorkspaceContainer({
  children,
  panel,
  panelOpen: panelOpenProp,
  className,
}: WorkspaceContainerProps) {
  const storePanelOpen = useUIStore((s) => s.panelOpen)
  const panelWidth = useUIStore((s) => s.panelWidth)

  const isOpen = panelOpenProp !== undefined ? panelOpenProp : storePanelOpen

  return (
    <div className={cn('flex h-full w-full overflow-hidden', className)}>
      {/* Main content */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">{children}</div>

      {/* Right panel */}
      {panel && isOpen && (
        <>
          <div
            className="w-px flex-shrink-0 bg-border"
            role="separator"
            aria-orientation="vertical"
          />
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
