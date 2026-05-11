import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Audit Log' }

export default function AuditPage() {
  return (
    <PageContainer title="Audit Log" description="Immutable event audit trail">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Audit Log — Phase 3+</p>
      </div>
    </PageContainer>
  )
}
