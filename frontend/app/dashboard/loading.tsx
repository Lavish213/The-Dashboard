import { PageContainer } from '@/components/workspace/PageContainer'
import { Skeleton } from '@/components/ui/skeleton'

export default function DashboardLoading() {
  return (
    <PageContainer title="Dashboard">
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-border p-4 space-y-2">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-7 w-28" />
              <Skeleton className="h-3 w-16" />
            </div>
          ))}
        </div>
        <Skeleton className="h-48 w-full rounded-lg" />
      </div>
    </PageContainer>
  )
}
