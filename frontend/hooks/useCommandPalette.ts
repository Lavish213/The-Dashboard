'use client'

import { useState, useCallback } from 'react'

interface UseCommandPaletteReturn {
  open: boolean
  openPalette: () => void
  closePalette: () => void
  togglePalette: () => void
  setOpen: (open: boolean) => void
}

/**
 * Controls open state for the command palette.
 * Use alongside CommandPalette component.
 */
export function useCommandPalette(): UseCommandPaletteReturn {
  const [open, setOpen] = useState(false)
  const openPalette  = useCallback(() => setOpen(true), [])
  const closePalette = useCallback(() => setOpen(false), [])
  const togglePalette = useCallback(() => setOpen((v) => !v), [])

  return { open, openPalette, closePalette, togglePalette, setOpen }
}
