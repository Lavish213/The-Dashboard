import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Activity' }

export default function ActivityPage() {
  return (
    <PageContainer title="Activity" description="System activity feed">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Activity — Phase 3+</p>
      </div>
    </PageContainer>
  )
}
