import * as React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export interface MetricCardProps {
  label: string
  value: string | number
  /** Secondary display value (e.g. unit or formatted) */
  unit?: string
  /** Percent or absolute change */
  change?: number
  changeLabel?: string
  changePeriod?: string
  /** Loading skeleton */
  loading?: boolean
  /** Icon in top-left */
  icon?: React.ReactNode
  /** Contextual color override */
  color?: 'default' | 'success' | 'warning' | 'destructive' | 'info'
  className?: string
  onClick?: () => void
}

function TrendIcon({ change }: { change: number }) {
  if (change > 0) return <TrendingUp className="h-3.5 w-3.5" />
  if (change < 0) return <TrendingDown className="h-3.5 w-3.5" />
  return <Minus className="h-3.5 w-3.5" />
}

const trendColor = (change: number) => {
  if (change > 0) return 'text-success'
  if (change < 0) return 'text-destructive'
  return 'text-muted-foreground'
}

export function MetricCard({
  label,
  value,
  unit,
  change,
  changeLabel,
  changePeriod,
  loading = false,
  icon,
  color = 'default',
  className,
  onClick,
}: MetricCardProps) {
  return (
    <Card
      className={cn(
        'transition-shadow',
        onClick && 'cursor-pointer hover:shadow-md',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <CardContent className="p-4">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-7 w-28" />
            <Skeleton className="h-3 w-16" />
          </div>
        ) : (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">{label}</p>
              {icon && (
                <span
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded text-muted-foreground',
                    color === 'success' && 'text-success',
                    color === 'warning' && 'text-warning',
                    color === 'destructive' && 'text-destructive',
                    color === 'info' && 'text-info'
                  )}
                >
                  {icon}
                </span>
              )}
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-semibold tracking-tight">
                {value}
              </span>
              {unit && (
                <span className="text-sm text-muted-foreground">{unit}</span>
              )}
            </div>
            {change !== undefined && (
              <div className={cn('flex items-center gap-1 text-xs', trendColor(change))}>
                <TrendIcon change={change} />
                <span>
                  {change > 0 ? '+' : ''}
                  {change}%
                  {changeLabel && ` ${changeLabel}`}
                </span>
                {changePeriod && (
                  <span className="text-muted-foreground">{changePeriod}</span>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
