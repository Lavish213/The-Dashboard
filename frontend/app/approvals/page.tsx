import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Approvals' }

export default function ApprovalsPage() {
  return (
    <PageContainer title="Approvals" description="Governance approval queue">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Approvals — Phase 7+</p>
      </div>
    </PageContainer>
  )
}
