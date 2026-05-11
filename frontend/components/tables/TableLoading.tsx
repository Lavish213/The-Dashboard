import * as React from 'react'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'

interface TableLoadingProps {
  /** Number of skeleton rows to show */
  rows?: number
  /** Number of columns */
  columns?: number
  compact?: boolean
  className?: string
}

export function TableLoading({
  rows = 8,
  columns = 5,
  compact = false,
  className,
}: TableLoadingProps) {
  return (
    <div className={cn('op-table-container', className)} aria-busy="true" aria-label="Loading table data">
      <table className={cn('op-table', compact && 'compact')}>
        <thead>
          <tr>
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i}>
                <Skeleton animation="pulse" className="h-3 w-24" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, rowIdx) => (
            <tr key={rowIdx}>
              {Array.from({ length: columns }).map((_, colIdx) => (
                <td key={colIdx}>
                  <Skeleton
                    animation="shimmer"
                    className="h-3"
                    style={{ width: `${60 + ((rowIdx * 3 + colIdx * 7) % 35)}%` }}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
