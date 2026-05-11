import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Transcript Detail' }

export default async function TranscriptDetailPage({
  params,
}: {
  params: Promise<{ callId: string }>
}) {
  const { callId } = await params
  return (
    <PageContainer title="Transcript">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Transcript {callId} — Phase 6+
        </p>
      </div>
    </PageContainer>
  )
}
