import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'
import { TranscriptViewer } from '@/features/transcripts/components/TranscriptViewer'

export const metadata: Metadata = { title: 'Transcript' }

export default async function TranscriptDetailPage({
  params,
}: {
  params: Promise<{ callId: string }>
}) {
  const { callId } = await params
  return (
    <PageContainer title="Transcript">
      <div className="h-full">
        <TranscriptViewer transcriptId={callId} />
      </div>
    </PageContainer>
  )
}
