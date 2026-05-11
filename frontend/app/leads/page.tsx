import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Leads' }

export default function LeadsPage() {
  return (
    <PageContainer title="Leads" description="Lead pipeline management">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Leads — Phase 5+</p>
      </div>
    </PageContainer>
  )
}
