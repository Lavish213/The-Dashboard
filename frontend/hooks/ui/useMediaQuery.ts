import { useEffect, useState } from 'react'

/**
 * Tracks whether a CSS media query matches.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    const mq = window.matchMedia(query)
    setMatches(mq.matches)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [query])

  return matches
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
export function useIsTablet()  { return useMediaQuery(breakpoints.md) && !useMediaQuery(breakpoints.lg) }
export function useIsDesktop() { return useMediaQuery(breakpoints.lg) }
