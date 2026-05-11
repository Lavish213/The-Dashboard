import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Analytics' }

export default function AnalyticsPage() {
  return (
    <PageContainer title="Analytics" description="Operational intelligence">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Analytics — Phase 8+</p>
      </div>
    </PageContainer>
  )
}
