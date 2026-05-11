'use client'

import { useEffect, useCallback } from 'react'

export interface KeyboardShortcut {
  key: string
  meta?: boolean
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
}

interface UseKeyboardShortcutOptions {
  preventDefault?: boolean
  /** Only active when this is true (default: true) */
  enabled?: boolean
}

/**
 * Registers a keyboard shortcut and calls `handler` when matched.
 */
export function useKeyboardShortcut(
  shortcut: KeyboardShortcut,
  handler: (e: KeyboardEvent) => void,
  options: UseKeyboardShortcutOptions = {}
) {
  const { preventDefault = false, enabled = true } = options

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return
      const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase()
      const metaMatch = shortcut.meta ? e.metaKey : !e.metaKey
      const ctrlMatch = shortcut.ctrl ? e.ctrlKey : !e.ctrlKey
      const shiftMatch = shortcut.shift ? e.shiftKey : true
      const altMatch = shortcut.alt ? e.altKey : true

      if (keyMatch && metaMatch && ctrlMatch && shiftMatch && altMatch) {
        if (preventDefault) e.preventDefault()
        handler(e)
      }
    },
    [enabled, shortcut, handler, preventDefault]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [handleKey])
}
