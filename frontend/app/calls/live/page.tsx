import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Live Calls' }

export default function LiveCallsPage() {
  return (
    <PageContainer title="Live Calls" description="Active calls in progress">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Live Calls — Phase 4+</p>
      </div>
    </PageContainer>
  )
}
