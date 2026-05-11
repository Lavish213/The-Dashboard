'use client'

/**
 * VirtualizedTable — Phase 1 shell.
 * Full virtualization (react-virtual) added in Phase 3.
 * For now, delegates to DataTable with a note.
 */

import * as React from 'react'
import { DataTable, type DataTableProps } from './DataTable'

export interface VirtualizedTableProps<TData extends Record<string, unknown>>
  extends DataTableProps<TData> {
  /** Estimated row height in px (used when virtualization is active) */
  estimatedRowHeight?: number
  /** Container height; required for virtual mode */
  containerHeight?: number
}

export function VirtualizedTable<TData extends Record<string, unknown>>({
  estimatedRowHeight: _estimatedRowHeight,
  containerHeight,
  ...props
}: VirtualizedTableProps<TData>) {
  const style = containerHeight ? { height: containerHeight, overflow: 'auto' } : undefined

  return (
    <div style={style}>
      {/* Phase 3: swap DataTable for react-virtual implementation */}
      <DataTable {...props} />
    </div>
  )
}
