'use client'

import * as React from 'react'
import { Settings2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import type { ColumnDef } from './DataTable'

interface TableColumnManagerProps<TData> {
  columns: ColumnDef<TData>[]
  hiddenColumns: Set<string>
  onHiddenChange: (hidden: Set<string>) => void
  className?: string
}

export function TableColumnManager<TData extends Record<string, unknown>>({
  columns,
  hiddenColumns,
  onHiddenChange,
  className,
}: TableColumnManagerProps<TData>) {
  const toggleColumn = (id: string) => {
    const next = new Set(hiddenColumns)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onHiddenChange(next)
  }

  const hideableColumns = columns.filter((c) => c.enableHiding !== false)

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn('h-8 gap-1.5 px-2 text-xs', className)}
          aria-label="Manage columns"
        >
          <Settings2 className="h-3.5 w-3.5" />
          Columns
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-48 p-2">
        <p className="mb-1.5 px-1 text-xs font-medium text-muted-foreground">
          Toggle columns
        </p>
        <div className="space-y-0.5">
          {hideableColumns.map((col) => {
            const isVisible = !hiddenColumns.has(col.id)
            const label =
              typeof col.header === 'string' ? col.header : col.id

            return (
              <label
                key={col.id}
                className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted"
              >
                <Checkbox
                  checked={isVisible}
                  onCheckedChange={() => toggleColumn(col.id)}
                  aria-label={`Toggle ${label} column`}
                />
                <span className="text-xs capitalize">{label}</span>
              </label>
            )
          })}
        </div>
      </PopoverContent>
    </Popover>
  )
}
