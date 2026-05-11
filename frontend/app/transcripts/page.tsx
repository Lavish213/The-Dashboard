import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Transcripts' }

export default function TranscriptsPage() {
  return (
    <PageContainer title="Transcripts" description="Call transcript intelligence">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Transcripts — Phase 6+</p>
      </div>
    </PageContainer>
  )
}
