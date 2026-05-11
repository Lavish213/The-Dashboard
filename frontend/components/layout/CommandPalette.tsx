'use client'

import * as React from 'react'
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from '@/components/ui/command'
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcuts'

export interface CommandGroup {
  id: string
  heading: string
  items: CommandItem[]
}

export interface CommandItem {
  id: string
  label: string
  description?: string
  icon?: React.ReactNode
  shortcut?: string
  onSelect: () => void
  keywords?: string[]
}

interface CommandPaletteProps {
  groups: CommandGroup[]
  open?: boolean
  onOpenChange?: (open: boolean) => void
  placeholder?: string
}

/**
 * CommandPalette — global command palette triggered by ⌘K / Ctrl+K.
 * Phase 1: static item list. Dynamic search + async results in Phase 2.
 */
export function CommandPalette({
  groups,
  open: controlledOpen,
  onOpenChange,
  placeholder = 'Type a command or search…',
}: CommandPaletteProps) {
  const [internalOpen, setInternalOpen] = React.useState(false)
  const open = controlledOpen ?? internalOpen
  const setOpen = onOpenChange ?? setInternalOpen

  useKeyboardShortcut(
    { key: 'k', meta: true },
    () => setOpen(!open),
    { preventDefault: true }
  )

  useKeyboardShortcut(
    { key: 'k', ctrl: true },
    () => setOpen(!open),
    { preventDefault: true }
  )

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder={placeholder} />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {groups.map((group, idx) => (
          <React.Fragment key={group.id}>
            {idx > 0 && <CommandSeparator />}
            <CommandGroup heading={group.heading}>
              {group.items.map((item) => (
                <CommandItem
                  key={item.id}
                  value={[item.label, ...(item.keywords ?? [])].join(' ')}
                  onSelect={() => {
                    item.onSelect()
                    setOpen(false)
                  }}
                >
                  {item.icon && (
                    <span className="mr-2 flex h-4 w-4 items-center justify-center">
                      {item.icon}
                    </span>
                  )}
                  <span>{item.label}</span>
                  {item.description && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      {item.description}
                    </span>
                  )}
                  {item.shortcut && (
                    <kbd className="ml-auto text-[10px] text-muted-foreground">
                      {item.shortcut}
                    </kbd>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </React.Fragment>
        ))}
      </CommandList>
    </CommandDialog>
  )
}
