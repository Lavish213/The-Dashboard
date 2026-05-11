import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Property Detail' }

export default async function PropertyDetailPage({
  params,
}: {
  params: Promise<{ propertyId: string }>
}) {
  const { propertyId } = await params
  return (
    <PageContainer title="Property Detail">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Property {propertyId} — Phase 5+
        </p>
      </div>
    </PageContainer>
  )
}
