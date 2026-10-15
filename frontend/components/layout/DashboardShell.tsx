'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface DashboardShellProps {
  sidebar?: React.ReactNode
  topbar?: React.ReactNode
  children: React.ReactNode
  /** Collapse sidebar to icon-only rail */
  sidebarCollapsed?: boolean
  className?: string
}

/**
 * DashboardShell — top-level operational layout.
 * Composes: fixed topbar + collapsible sidebar + scrollable main content area.
 * Phase 1: static layout only. Sidebar collapse persistence added in Phase 2.
 */
export function DashboardShell({
  sidebar,
  topbar,
  children,
  sidebarCollapsed = false,
  className,
}: DashboardShellProps) {
  const sidebarWidth = sidebarCollapsed ? 'w-14' : 'w-[var(--sidebar-width,280px)]'

  return (
    <div className={cn('flex h-screen w-full overflow-hidden bg-background text-foreground', className)}>
      {/* Sidebar */}
      {sidebar && (
        <aside
          className={cn(
            'flex-shrink-0 border-r border-border transition-[width] duration-200',
            sidebarWidth
          )}
          aria-label="Sidebar navigation"
        >
          {sidebar}
        </aside>
      )}

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar */}
        {topbar && (
          <header
            className="flex-shrink-0 border-b border-border"
            style={{ height: 'var(--header-height, 48px)' }}
          >
            {topbar}
          </header>
        )}

        {/* Content */}
        <main className="flex-1 overflow-auto" role="main">
          {children}
        </main>
      </div>
    </div>
  )
}
