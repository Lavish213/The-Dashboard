'use client'

import * as React from 'react'
import { useCommandStore } from '@/stores/command.store'
import { CommandPalette } from '@/components/layout/CommandPalette'
import { useNavigation } from '@/hooks/navigation/useNavigation'
import { NAV_ROUTES } from '@/lib/navigation/routes'
import type { CommandGroup } from '@/components/layout/CommandPalette'

/**
 * CommandPaletteProvider — mounts the global command palette.
 * Populated with navigation items; extended with search in Phase 3+.
 */
export function CommandPaletteProvider() {
  const open = useCommandStore((s) => s.open)
  const setOpen = useCommandStore((s) => s.setOpen)
  const { navigate } = useNavigation()

  const groups: CommandGroup[] = [
    {
      id: 'navigate',
      heading: 'Navigate',
      items: NAV_ROUTES.map((route) => {
        const Icon = route.icon
        return {
          id: route.id,
          label: route.label,
          icon: <Icon className="h-4 w-4" />,
          onSelect: () => navigate(route.href),
          keywords: [route.group, route.href],
        }
      }),
    },
  ]

  return (
    <CommandPalette
      groups={groups}
      open={open}
      onOpenChange={setOpen}
      placeholder="Navigate to…"
    />
  )
}
