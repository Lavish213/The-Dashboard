'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Checkbox } from '@/components/ui/checkbox'
import { TableEmptyState } from './TableEmptyState'
import { TableLoading } from './TableLoading'

export interface ColumnDef<TData> {
  id: string
  header: React.ReactNode | ((ctx: { table: TableInstance<TData> }) => React.ReactNode)
  cell: (ctx: { row: TData; index: number }) => React.ReactNode
  /** Width CSS value */
  width?: string
  minWidth?: string
  /** Pin to left or right */
  pin?: 'left' | 'right'
  enableSorting?: boolean
  enableHiding?: boolean
  meta?: Record<string, unknown>
}

export interface SortState {
  id: string
  desc: boolean
}

export interface TableInstance<TData> {
  rows: TData[]
  selectedIds: Set<string>
  toggleAllSelected: () => void
  allSelected: boolean
  someSelected: boolean
  sort: SortState | null
  setSort: (id: string) => void
  visibleColumnIds: Set<string>
}

export interface DataTableProps<TData> {
  data: TData[]
  columns: ColumnDef<TData>[]
  /** Fn to get stable row id */
  getRowId?: (row: TData) => string
  /** Loading state */
  loading?: boolean
  /** Controlled selection */
  selectedIds?: Set<string>
  onSelectionChange?: (ids: Set<string>) => void
  /** Controlled sort */
  sort?: SortState | null
  onSortChange?: (sort: SortState | null) => void
  /** Hide columns by id */
  hiddenColumns?: Set<string>
  /** Row click handler */
  onRowClick?: (row: TData) => void
  /** Empty state */
  emptyTitle?: string
  emptyDescription?: string
  emptyAction?: React.ReactNode
  /** Compact row height */
  compact?: boolean
  /** Sticky header */
  stickyHeader?: boolean
  className?: string
  'aria-label'?: string
}

type SortDir = 'asc' | 'desc' | null

function nextSort(current: SortDir, id: string, activeId: string | null): SortState | null {
  if (activeId !== id) return { id, desc: false }
  if (!current) return { id, desc: false }
  if (current === 'asc') return { id, desc: true }
  return null
}

export function DataTable<TData extends Record<string, unknown>>({
  data,
  columns,
  getRowId,
  loading = false,
  selectedIds: controlledSelected,
  onSelectionChange,
  sort: controlledSort,
  onSortChange,
  hiddenColumns,
  onRowClick,
  emptyTitle,
  emptyDescription,
  emptyAction,
  compact = false,
  stickyHeader = true,
  className,
  'aria-label': ariaLabel,
}: DataTableProps<TData>) {
  const [internalSelected, setInternalSelected] = React.useState<Set<string>>(new Set())
  const [internalSort, setInternalSort] = React.useState<SortState | null>(null)

  const selectedIds = controlledSelected ?? internalSelected
  const sort = controlledSort !== undefined ? controlledSort : internalSort

  const setSelection = React.useCallback(
    (next: Set<string>) => {
      if (!controlledSelected) setInternalSelected(next)
      onSelectionChange?.(next)
    },
    [controlledSelected, onSelectionChange]
  )

  const setSort = React.useCallback(
    (colId: string) => {
      const currentDir: SortDir = sort?.id === colId ? (sort.desc ? 'desc' : 'asc') : null
      const next = nextSort(currentDir, colId, sort?.id ?? null)
      if (!controlledSort !== undefined) setInternalSort(next)
      onSortChange?.(next)
    },
    [sort, controlledSort, onSortChange]
  )

  const visibleColumnIds = React.useMemo(() => {
    const all = new Set(columns.map((c) => c.id))
    if (!hiddenColumns) return all
    return new Set([...all].filter((id) => !hiddenColumns.has(id)))
  }, [columns, hiddenColumns])

  const visibleColumns = React.useMemo(
    () => columns.filter((c) => visibleColumnIds.has(c.id)),
    [columns, visibleColumnIds]
  )

  const rowIds = React.useMemo(
    () => data.map((row, i) => (getRowId ? getRowId(row) : String(i))),
    [data, getRowId]
  )

  const allSelected = rowIds.length > 0 && rowIds.every((id) => selectedIds.has(id))
  const someSelected = rowIds.some((id) => selectedIds.has(id)) && !allSelected

  const toggleAllSelected = React.useCallback(() => {
    if (allSelected) {
      setSelection(new Set())
    } else {
      setSelection(new Set(rowIds))
    }
  }, [allSelected, rowIds, setSelection])

  const toggleRow = React.useCallback(
    (id: string) => {
      const next = new Set(selectedIds)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      setSelection(next)
    },
    [selectedIds, setSelection]
  )

  const tableInstance: TableInstance<TData> = {
    rows: data,
    selectedIds,
    toggleAllSelected,
    allSelected,
    someSelected,
    sort,
    setSort,
    visibleColumnIds,
  }

  const hasSelection = onSelectionChange !== undefined

  if (loading) {
    return <TableLoading columns={visibleColumns.length + (hasSelection ? 1 : 0)} compact={compact} />
  }

  if (!data.length) {
    return (
      <TableEmptyState
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
      />
    )
  }

  return (
    <div className={cn('op-table-container', className)}>
      <table
        className={cn('op-table', compact && 'compact')}
        aria-label={ariaLabel}
      >
        <thead className={cn(stickyHeader && 'sticky top-0 z-10')}>
          <tr>
            {hasSelection && (
              <th className="w-10 px-3" aria-label="Select all">
                <Checkbox
                  checked={allSelected ? true : someSelected ? 'indeterminate' : false}
                  onCheckedChange={toggleAllSelected}
                  aria-label="Select all rows"
                />
              </th>
            )}
            {visibleColumns.map((col) => {
              const canSort = col.enableSorting !== false
              const isActive = sort?.id === col.id
              const headerContent =
                typeof col.header === 'function'
                  ? col.header({ table: tableInstance })
                  : col.header

              return (
                <th
                  key={col.id}
                  style={{
                    width: col.width,
                    minWidth: col.minWidth,
                  }}
                  className={cn(
                    canSort && 'cursor-pointer select-none',
                    col.pin === 'left' && 'sticky-left',
                    col.pin === 'right' && 'sticky-right',
                    isActive && 'sort-asc',
                    isActive && sort?.desc && 'sort-desc'
                  )}
                  onClick={canSort ? () => setSort(col.id) : undefined}
                  aria-sort={
                    isActive ? (sort?.desc ? 'descending' : 'ascending') : undefined
                  }
                >
                  {headerContent}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => {
            const rowId = rowIds[index]
            const isSelected = selectedIds.has(rowId)

            return (
              <tr
                key={rowId}
                className={cn(
                  onRowClick && 'cursor-pointer',
                  isSelected && 'selected'
                )}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                aria-selected={isSelected}
              >
                {hasSelection && (
                  <td className="w-10 px-3" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => toggleRow(rowId)}
                      aria-label={`Select row ${index + 1}`}
                    />
                  </td>
                )}
                {visibleColumns.map((col) => (
                  <td
                    key={col.id}
                    className={cn(
                      col.pin === 'left' && 'sticky-left',
                      col.pin === 'right' && 'sticky-right'
                    )}
                  >
                    {col.cell({ row, index })}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
