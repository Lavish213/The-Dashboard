import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const gridVariants = cva('grid', {
  variants: {
    cols: {
      1:    'grid-cols-1',
      2:    'grid-cols-2',
      3:    'grid-cols-3',
      4:    'grid-cols-4',
      5:    'grid-cols-5',
      6:    'grid-cols-6',
      12:   'grid-cols-12',
      auto: 'grid-cols-[repeat(auto-fill,minmax(280px,1fr))]',
    },
    gap: {
      0: 'gap-0',
      2: 'gap-2',
      3: 'gap-3',
      4: 'gap-4',
      6: 'gap-6',
      8: 'gap-8',
    },
    rows: {
      1: 'grid-rows-1',
      2: 'grid-rows-2',
      3: 'grid-rows-3',
      auto: 'grid-rows-[auto]',
    },
  },
  defaultVariants: {
    cols: 1,
    gap: 4,
  },
})

export interface GridProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof gridVariants> {}

export function Grid({ className, cols, gap, rows, ...props }: GridProps) {
  return (
    <div className={cn(gridVariants({ cols, gap, rows }), className)} {...props} />
  )
}

/** Responsive 2-col on sm, 3-col on lg */
export function MetricGrid({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4', className)}
      {...props}
    />
  )
}

/** Responsive dashboard grid: sidebar + main */
export function DashboardGrid({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]', className)}
      {...props}
    />
  )
}
