import { useCallback, useSyncExternalStore } from 'react'

/**
 * Tracks whether a CSS media query matches.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback((notify: () => void) => {
    const mq = window.matchMedia(query)
    mq.addEventListener('change', notify)
    return () => mq.removeEventListener('change', notify)
  }, [query])
  const snapshot = useCallback(() => window.matchMedia(query).matches, [query])
  return useSyncExternalStore(subscribe, snapshot, () => false)
}

/** Tailwind breakpoint shorthands */
export const breakpoints = {
  sm:  '(min-width: 640px)',
  md:  '(min-width: 768px)',
  lg:  '(min-width: 1024px)',
  xl:  '(min-width: 1280px)',
  '2xl': '(min-width: 1536px)',
} as const

export function useIsMobile()  { return !useMediaQuery(breakpoints.md) }
export function useIsTablet() {
  const medium = useMediaQuery(breakpoints.md)
  const large = useMediaQuery(breakpoints.lg)
  return medium && !large
}
export function useIsDesktop() { return useMediaQuery(breakpoints.lg) }
