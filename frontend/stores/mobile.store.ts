import { create } from 'zustand'

interface MobileState {
  // Mobile nav drawer
  mobileNavOpen: boolean
  setMobileNavOpen: (open: boolean) => void
  toggleMobileNav: () => void

  // Detected mobile breakpoint state
  isMobile: boolean
  isTablet: boolean
  setBreakpoint: (isMobile: boolean, isTablet: boolean) => void

  // Active bottom nav tab (for mobile)
  activeBottomTab: string
  setActiveBottomTab: (tab: string) => void
}

export const useMobileStore = create<MobileState>()((set) => ({
  mobileNavOpen: false,
  setMobileNavOpen: (open) => set({ mobileNavOpen: open }),
  toggleMobileNav: () => set((s) => ({ mobileNavOpen: !s.mobileNavOpen })),

  isMobile: false,
  isTablet: false,
  setBreakpoint: (isMobile, isTablet) => set({ isMobile, isTablet }),

  activeBottomTab: 'dashboard',
  setActiveBottomTab: (tab) => set({ activeBottomTab: tab }),
}))
