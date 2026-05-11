import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type DensitySetting = 'compact' | 'default' | 'comfortable'

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void

  // Right panel (detail/inspector)
  panelOpen: boolean
  panelWidth: number
  setPanelOpen: (open: boolean) => void
  setPanelWidth: (width: number) => void
  togglePanel: () => void

  // Density
  density: DensitySetting
  setDensity: (density: DensitySetting) => void

  // Full-screen mode
  fullscreen: boolean
  setFullscreen: (v: boolean) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Sidebar
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

      // Panel
      panelOpen: false,
      panelWidth: 420,
      setPanelOpen: (open) => set({ panelOpen: open }),
      setPanelWidth: (width) => set({ panelWidth: Math.max(280, Math.min(800, width)) }),
      togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),

      // Density
      density: 'default',
      setDensity: (density) => set({ density }),

      // Fullscreen
      fullscreen: false,
      setFullscreen: (fullscreen) => set({ fullscreen }),
    }),
    {
      name: 'karpathys:ui',
      partialize: (s) => ({
        sidebarCollapsed: s.sidebarCollapsed,
        panelWidth: s.panelWidth,
        density: s.density,
      }),
    }
  )
)
