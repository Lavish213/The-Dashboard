'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

export interface FilterOption {
  value: string
  label: string
  count?: number
}

export interface FilterDef {
  id: string
  label: string
  options: FilterOption[]
  multiple?: boolean
}

export interface ActiveFilter {
  filterId: string
  value: string
}

interface TableFiltersProps {
  filters: FilterDef[]
  activeFilters: ActiveFilter[]
  onFilterChange: (filters: ActiveFilter[]) => void
  className?: string
}

export function TableFilters({
  filters,
  activeFilters,
  onFilterChange,
  className,
}: TableFiltersProps) {
  const toggle = React.useCallback(
    (filterId: string, value: string, multiple?: boolean) => {
      const existing = activeFilters.find(
        (f) => f.filterId === filterId && f.value === value
      )
      if (existing) {
        onFilterChange(
          activeFilters.filter((f) => !(f.filterId === filterId && f.value === value))
        )
        return
      }
      if (!multiple) {
        const next = activeFilters.filter((f) => f.filterId !== filterId)
        onFilterChange([...next, { filterId, value }])
      } else {
        onFilterChange([...activeFilters, { filterId, value }])
      }
    },
    [activeFilters, onFilterChange]
  )

  const clearAll = React.useCallback(() => onFilterChange([]), [onFilterChange])

  const isActive = (filterId: string, value: string) =>
    activeFilters.some((f) => f.filterId === filterId && f.value === value)

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      {filters.map((filter) => (
        <div key={filter.id} className="flex items-center gap-1">
          <span className="text-xs text-muted-foreground">{filter.label}:</span>
          {filter.options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => toggle(filter.id, opt.value, filter.multiple)}
              className={cn(
                'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs transition-colors',
                isActive(filter.id, opt.value)
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-transparent text-muted-foreground hover:border-foreground/30 hover:text-foreground'
              )}
            >
              {opt.label}
              {opt.count !== undefined && (
                <span className="text-[10px] opacity-70">{opt.count}</span>
              )}
            </button>
          ))}
        </div>
      ))}

      {activeFilters.length > 0 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={clearAll}
          className="h-6 px-2 text-xs text-muted-foreground"
        >
          <X className="mr-1 h-3 w-3" />
          Clear
        </Button>
      )}
    </div>
  )
}

/** Chip-style active filter pills */
export function ActiveFilterPills({
  filters,
  activeFilters,
  onRemove,
  className,
}: {
  filters: FilterDef[]
  activeFilters: ActiveFilter[]
  onRemove: (filter: ActiveFilter) => void
  className?: string
}) {
  if (!activeFilters.length) return null

  const getLabel = (filterId: string, value: string) => {
    const filter = filters.find((f) => f.id === filterId)
    const opt = filter?.options.find((o) => o.value === value)
    return opt ? `${filter!.label}: ${opt.label}` : value
  }

  return (
    <div className={cn('flex flex-wrap gap-1', className)}>
      {activeFilters.map((af) => (
        <Badge
          key={`${af.filterId}:${af.value}`}
          variant="secondary"
          className="gap-1 pr-1 text-xs"
        >
          {getLabel(af.filterId, af.value)}
          <button
            onClick={() => onRemove(af)}
            className="ml-0.5 rounded-sm opacity-60 hover:opacity-100"
            aria-label={`Remove filter ${getLabel(af.filterId, af.value)}`}
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}
    </div>
  )
}
