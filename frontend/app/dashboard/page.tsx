import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Dashboard' }

export default function DashboardPage() {
  return (
    <PageContainer title="Dashboard" description="Operational overview">
      {/* Phase 3+ — metrics, alerts, and workflow status implemented with backend */}
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Dashboard — Phase 3+</p>
      </div>
    </PageContainer>
  )
}
