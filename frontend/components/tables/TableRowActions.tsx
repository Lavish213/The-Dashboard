'use client'

import * as React from 'react'
import { MoreHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

export interface RowAction<TData> {
  id: string
  label: string
  icon?: React.ReactNode
  onClick: (row: TData) => void
  /** Show red destructive styling */
  destructive?: boolean
  /** Hide action conditionally */
  hidden?: (row: TData) => boolean
  /** Disable action conditionally */
  disabled?: (row: TData) => boolean
  separator?: boolean
}

interface TableRowActionsProps<TData> {
  row: TData
  actions: RowAction<TData>[]
  /** Custom trigger label */
  triggerLabel?: string
  className?: string
}

export function TableRowActions<TData>({
  row,
  actions,
  triggerLabel = 'Open row actions',
  className,
}: TableRowActionsProps<TData>) {
  const visibleActions = actions.filter((a) => !a.hidden?.(row))

  if (!visibleActions.length) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn('h-7 w-7 p-0', className)}
          aria-label={triggerLabel}
          onClick={(e) => e.stopPropagation()}
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[140px]">
        {visibleActions.map((action, idx) => (
          <React.Fragment key={action.id}>
            {action.separator && idx > 0 && <DropdownMenuSeparator />}
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                action.onClick(row)
              }}
              disabled={action.disabled?.(row)}
              className={cn(
                'gap-2',
                action.destructive &&
                  'text-destructive focus:bg-destructive/10 focus:text-destructive'
              )}
            >
              {action.icon && (
                <span className="flex h-4 w-4 items-center justify-center">
                  {action.icon}
                </span>
              )}
              {action.label}
            </DropdownMenuItem>
          </React.Fragment>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
