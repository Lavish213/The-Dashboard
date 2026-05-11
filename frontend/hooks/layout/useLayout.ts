'use client'

import { useUIStore, type DensitySetting } from '@/stores/ui.store'
import { useMobileStore } from '@/stores/mobile.store'

export interface UseLayoutReturn {
  // Sidebar
  sidebarCollapsed: boolean
  toggleSidebar: () => void

  // Panel
  panelOpen: boolean
  panelWidth: number
  togglePanel: () => void
  setPanelWidth: (w: number) => void
  setPanelOpen: (open: boolean) => void

  // Density
  density: DensitySetting
  setDensity: (d: DensitySetting) => void

  // Mobile
  isMobile: boolean
  isTablet: boolean
  mobileNavOpen: boolean
  toggleMobileNav: () => void
}

/**
 * Composite layout state hook for shell components.
 * Aggregates sidebar, panel, density, and mobile state.
 */
export function useLayout(): UseLayoutReturn {
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const panelOpen = useUIStore((s) => s.panelOpen)
  const panelWidth = useUIStore((s) => s.panelWidth)
  const togglePanel = useUIStore((s) => s.togglePanel)
  const setPanelWidth = useUIStore((s) => s.setPanelWidth)
  const setPanelOpen = useUIStore((s) => s.setPanelOpen)
  const density = useUIStore((s) => s.density)
  const setDensity = useUIStore((s) => s.setDensity)

  const isMobile = useMobileStore((s) => s.isMobile)
  const isTablet = useMobileStore((s) => s.isTablet)
  const mobileNavOpen = useMobileStore((s) => s.mobileNavOpen)
  const toggleMobileNav = useMobileStore((s) => s.toggleMobileNav)

  return {
    sidebarCollapsed,
    toggleSidebar,
    panelOpen,
    panelWidth,
    togglePanel,
    setPanelWidth,
    setPanelOpen,
    density,
    setDensity,
    isMobile,
    isTablet,
    mobileNavOpen,
    toggleMobileNav,
  }
}
