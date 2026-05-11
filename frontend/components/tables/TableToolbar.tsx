'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Search, RefreshCw, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface TableToolbarProps {
  /** Search value (controlled) */
  search?: string
  onSearchChange?: (value: string) => void
  searchPlaceholder?: string
  /** Left slot: filters, segment controls, etc. */
  left?: React.ReactNode
  /** Right slot: actions, column manager, export, etc. */
  right?: React.ReactNode
  /** Show refresh button */
  onRefresh?: () => void
  refreshing?: boolean
  /** Show export button */
  onExport?: () => void
  /** Selection count — shows bulk-action slot */
  selectedCount?: number
  bulkActions?: React.ReactNode
  className?: string
}

export function TableToolbar({
  search,
  onSearchChange,
  searchPlaceholder = 'Search…',
  left,
  right,
  onRefresh,
  refreshing = false,
  onExport,
  selectedCount = 0,
  bulkActions,
  className,
}: TableToolbarProps) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div className="flex items-center gap-2">
        {/* Search */}
        {onSearchChange !== undefined && (
          <div className="relative max-w-xs flex-1">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search ?? ''}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              className="h-8 pl-8 text-sm"
            />
          </div>
        )}

        {/* Left slot */}
        {left && <div className="flex items-center gap-2">{left}</div>}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right slot */}
        {right && <div className="flex items-center gap-2">{right}</div>}

        {onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={refreshing}
            className="h-8 w-8 p-0"
            aria-label="Refresh"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', refreshing && 'animate-spin')} />
          </Button>
        )}

        {onExport && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onExport}
            className="h-8 w-8 p-0"
            aria-label="Export"
          >
            <Download className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* Bulk action bar */}
      {selectedCount > 0 && bulkActions && (
        <div className="flex items-center gap-2 rounded-md border border-primary/30 bg-primary/5 px-3 py-1.5">
          <span className="text-xs font-medium text-primary">
            {selectedCount} selected
          </span>
          <div className="h-3.5 w-px bg-border" />
          <div className="flex items-center gap-1">{bulkActions}</div>
        </div>
      )}
    </div>
  )
}
