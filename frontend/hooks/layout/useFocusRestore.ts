'use client'

import { useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'

/**
 * Restores focus to the main content area on route change.
 * Accessibility requirement: focus must move to meaningful content after navigation.
 */
export function useFocusRestore() {
  const pathname = usePathname()
  const ref = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (ref.current) {
      ref.current.focus({ preventScroll: true })
    }
  }, [pathname])

  return ref
}
