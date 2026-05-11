import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const skeletonVariants = cva('rounded', {
  variants: {
    animation: {
      pulse:   'animate-pulse bg-muted',
      shimmer: 'animate-shimmer bg-gradient-to-r from-muted via-muted/40 to-muted bg-[length:200%_100%]',
      none:    'bg-muted',
    },
  },
  defaultVariants: {
    animation: 'pulse',
  },
})

export interface SkeletonProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonVariants> {}

function Skeleton({ className, animation, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(skeletonVariants({ animation }), className)}
      aria-hidden="true"
      {...props}
    />
  )
}

/** Pre-built skeleton shapes for common use cases */
function SkeletonText({ lines = 1, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('space-y-2', className)} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn('h-3', i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full')}
        />
      ))}
    </div>
  )
}

function SkeletonAvatar({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClass = { sm: 'h-7 w-7', md: 'h-9 w-9', lg: 'h-11 w-11' }[size]
  return <Skeleton className={cn('rounded-full shrink-0', sizeClass)} />
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 px-3 py-2" aria-hidden="true">
      <SkeletonAvatar size="sm" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="h-2.5 w-1/2" />
      </div>
      <Skeleton className="h-5 w-14 rounded-full" />
    </div>
  )
}

export { Skeleton, SkeletonText, SkeletonAvatar, SkeletonRow }
