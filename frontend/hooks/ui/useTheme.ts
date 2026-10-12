'use client'

import { useTheme as useNextTheme } from 'next-themes'
import { useSyncExternalStore } from 'react'

const subscribeToMount = () => () => {}

export type Theme = 'light' | 'dark' | 'system'

export interface UseThemeReturn {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  isDark: boolean
  isLight: boolean
  mounted: boolean
}

/**
 * Thin wrapper around next-themes with operational conveniences.
 * Always check `mounted` before reading theme to avoid hydration mismatch.
 */
export function useTheme(): UseThemeReturn {
  const { theme, resolvedTheme, setTheme } = useNextTheme()
  const mounted = useSyncExternalStore(subscribeToMount, () => true, () => false)

  const resolved = (resolvedTheme ?? 'dark') as 'light' | 'dark'

  const toggleTheme = () => {
    setTheme(resolved === 'dark' ? 'light' : 'dark')
  }

  return {
    theme: (theme ?? 'dark') as Theme,
    resolvedTheme: resolved,
    setTheme: setTheme as (t: Theme) => void,
    toggleTheme,
    isDark: resolved === 'dark',
    isLight: resolved === 'light',
    mounted,
  }
}
