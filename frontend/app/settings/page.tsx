import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'

export const metadata: Metadata = { title: 'Settings' }

export default function SettingsPage() {
  return (
    <PageContainer title="Settings">
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Settings — Phase 3+</p>
      </div>
    </PageContainer>
  )
}
