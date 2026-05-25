import { cn } from '@/lib/utils'

function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn('animate-pulse rounded-md bg-muted', className)} />
  )
}

export function SkeletonCard() {
  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-3 w-1/4" />
    </div>
  )
}

export function SkeletonKpiGrid() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
    </div>
  )
}

export function SkeletonTable({ rows = 8, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <div className="border-b border-border px-4 py-3 flex gap-4">
        {[...Array(cols)].map((_, i) => (
          <Skeleton key={i} className="h-3 w-20" />
        ))}
      </div>
      {[...Array(rows)].map((_, i) => (
        <div key={i} className="border-b border-border last:border-0 px-4 py-3 flex gap-4">
          {[...Array(cols)].map((_, j) => (
            <Skeleton key={j} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonKanban() {
  return (
    <div className="flex gap-3 overflow-x-auto pb-4">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="min-w-[220px] flex-shrink-0 space-y-2">
          <Skeleton className="h-4 w-20 mb-3" />
          {[...Array(i === 0 ? 3 : i === 1 ? 2 : 1)].map((_, j) => (
            <div key={j} className="rounded-lg border bg-card p-3 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
              <Skeleton className="h-6 w-full" />
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonFeed({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {[...Array(rows)].map((_, i) => (
        <div key={i} className="flex items-start gap-3 rounded-lg border bg-card px-4 py-3">
          <Skeleton className="h-2 w-2 rounded-full mt-1.5 flex-shrink-0" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </div>
          <Skeleton className="h-3 w-20 flex-shrink-0" />
        </div>
      ))}
    </div>
  )
}

export function SkeletonDetail() {
  return (
    <div className="rounded-lg border bg-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-1/3" />
        <Skeleton className="h-5 w-16" />
      </div>
      {[...Array(4)].map((_, i) => (
        <div key={i} className="flex gap-3">
          <div className="flex flex-col items-center flex-shrink-0">
            <Skeleton className="h-2 w-2 rounded-full" />
            {i < 3 && <div className="w-px flex-1 bg-border mt-1 min-h-8" />}
          </div>
          <div className="flex-1 pb-3 space-y-1.5">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-1/3" />
          </div>
        </div>
      ))}
    </div>
  )
}