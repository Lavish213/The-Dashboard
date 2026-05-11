'use client'

import * as React from 'react'
import * as ProgressPrimitive from '@radix-ui/react-progress'
import { cn } from '@/lib/utils'

interface ProgressProps
  extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> {
  variant?: 'default' | 'success' | 'warning' | 'destructive'
  size?: 'sm' | 'default' | 'lg'
  showValue?: boolean
}

const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  ProgressProps
>(({ className, value, variant = 'default', size = 'default', showValue, ...props }, ref) => {
  const sizeClass = { sm: 'h-1', default: 'h-2', lg: 'h-3' }[size]
  const indicatorClass = {
    default:     'bg-primary',
    success:     'bg-success',
    warning:     'bg-warning',
    destructive: 'bg-destructive',
  }[variant]

  return (
    <div className="flex items-center gap-2">
      <ProgressPrimitive.Root
        ref={ref}
        className={cn(
          'relative w-full overflow-hidden rounded-full bg-secondary',
          sizeClass,
          className
        )}
        {...props}
      >
        <ProgressPrimitive.Indicator
          className={cn('h-full w-full flex-1 transition-all', indicatorClass)}
          style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
        />
      </ProgressPrimitive.Root>
      {showValue && (
        <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
          {value ?? 0}%
        </span>
      )}
    </div>
  )
})
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
