import type { Metadata } from 'next'
import { WorkflowDetailView } from '@/features/workflows/WorkflowDetailView'

export const metadata: Metadata = { title: 'Workflow Detail' }

export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ workflowId: string }>
}) {
  const { workflowId } = await params
  return <WorkflowDetailView workflowId={workflowId} />
}
