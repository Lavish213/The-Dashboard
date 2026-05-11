import { PageContainer } from '@/components/workspace/PageContainer'
import { TableLoading } from '@/components/tables/TableLoading'

export default function CallsLoading() {
  return (
    <PageContainer title="Calls">
      <TableLoading rows={10} columns={5} />
    </PageContainer>
  )
}
