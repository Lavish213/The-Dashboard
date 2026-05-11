import { PageContainer } from '@/components/workspace/PageContainer'
import { TableLoading } from '@/components/tables/TableLoading'

export default function WorkflowsLoading() {
  return (
    <PageContainer title="Workflows">
      <TableLoading rows={8} columns={5} />
    </PageContainer>
  )
}
