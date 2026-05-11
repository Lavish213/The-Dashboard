import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Workflows' }

export default function WorkflowsPage() {
  return (
    <PageContainer title="Workflows" description="Workflow orchestration">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Workflows — Phase 5+</p>
      </div>
    </PageContainer>
  )
}
