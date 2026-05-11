'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface TablePaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (size: number) => void
  pageSizeOptions?: number[]
  className?: string
}

export function TablePagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50, 100],
  className,
}: TablePaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  return (
    <div
      className={cn('flex items-center justify-between gap-4 py-2', className)}
      aria-label="Pagination"
    >
      {/* Row count */}
      <p className="text-xs text-muted-foreground">
        {total === 0
          ? 'No results'
          : `${from}–${to} of ${total.toLocaleString()}`}
      </p>

      <div className="flex items-center gap-2">
        {/* Page size selector */}
        {onPageSizeChange && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Rows</span>
            <Select
              value={String(pageSize)}
              onValueChange={(v) => onPageSizeChange(Number(v))}
            >
              <SelectTrigger className="h-7 w-16 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {pageSizeOptions.map((size) => (
                  <SelectItem key={size} value={String(size)} className="text-xs">
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Nav buttons */}
        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(1)}
            disabled={page <= 1}
            className="h-7 w-7 p-0"
            aria-label="First page"
          >
            <ChevronsLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="h-7 w-7 p-0"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>

          <span className="min-w-[4rem] text-center text-xs text-muted-foreground">
            {page} / {pageCount}
          </span>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pageCount}
            className="h-7 w-7 p-0"
            aria-label="Next page"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(pageCount)}
            disabled={page >= pageCount}
            className="h-7 w-7 p-0"
            aria-label="Last page"
          >
            <ChevronsRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  )
}
