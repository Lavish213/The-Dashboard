import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Calls' }

export default function CallsPage() {
  return (
    <PageContainer title="Calls" description="Call history and management">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Calls — Phase 5+</p>
      </div>
    </PageContainer>
  )
}
