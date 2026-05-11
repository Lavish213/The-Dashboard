import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Lead Detail' }

export default async function LeadDetailPage({
  params,
}: {
  params: Promise<{ leadId: string }>
}) {
  const { leadId } = await params
  return (
    <PageContainer title="Lead Detail">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Lead {leadId} — Phase 5+
        </p>
      </div>
    </PageContainer>
  )
}
