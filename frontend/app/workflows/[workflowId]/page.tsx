import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Workflow Detail' }

export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ workflowId: string }>
}) {
  const { workflowId } = await params
  return (
    <PageContainer title="Workflow Detail">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Workflow {workflowId} — Phase 5+
        </p>
      </div>
    </PageContainer>
  )
}
