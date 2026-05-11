import { PageContainer } from '@/components/workspace/PageContainer'
import { Skeleton } from '@/components/ui/skeleton'

export default function ApprovalsLoading() {
  return (
    <PageContainer title="Approvals">
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border p-4 space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-64" />
            <Skeleton className="h-3 w-32" />
          </div>
        ))}
      </div>
    </PageContainer>
  )
}
