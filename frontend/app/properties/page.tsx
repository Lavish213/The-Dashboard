import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Properties' }

export default function PropertiesPage() {
  return (
    <PageContainer title="Properties" description="Property inventory">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Properties — Phase 5+</p>
      </div>
    </PageContainer>
  )
}
