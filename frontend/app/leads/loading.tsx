import { PageContainer } from '@/components/workspace/PageContainer'
import { TableLoading } from '@/components/tables/TableLoading'

export default function LeadsLoading() {
  return (
    <PageContainer title="Leads">
      <TableLoading rows={10} columns={6} />
    </PageContainer>
  )
}
