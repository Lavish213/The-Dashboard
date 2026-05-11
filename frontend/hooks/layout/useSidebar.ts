'use client'

import { useCallback } from 'react'
import { useUIStore } from '@/stores/ui.store'

export interface UseSidebarReturn {
  collapsed: boolean
  collapse: () => void
  expand: () => void
  toggle: () => void
  setCollapsed: (v: boolean) => void
}

/**
 * Sidebar state management hook.
 * State is persisted to localStorage via Zustand persist middleware.
 */
export function useSidebar(): UseSidebarReturn {
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const setSidebarCollapsed = useUIStore((s) => s.setSidebarCollapsed)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)

  const collapse = useCallback(() => setSidebarCollapsed(true), [setSidebarCollapsed])
  const expand = useCallback(() => setSidebarCollapsed(false), [setSidebarCollapsed])

  return {
    collapsed,
    collapse,
    expand,
    toggle: toggleSidebar,
    setCollapsed: setSidebarCollapsed,
  }
}
