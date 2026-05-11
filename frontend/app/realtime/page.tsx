import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'
import { RealtimeMonitor } from '@/features/realtime/RealtimeMonitor'

export const metadata: Metadata = { title: 'Realtime' }

export default function RealtimePage() {
  return (
    <PageContainer title="Realtime" description="Live event stream monitor">
      <RealtimeMonitor />
    </PageContainer>
  )
}
