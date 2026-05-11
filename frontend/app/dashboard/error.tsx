'use client'

import { useEffect } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { Button } from '@/components/ui/button'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('[Dashboard]', error)
  }, [error])

  return (
    <PageContainer title="Dashboard">
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <p className="text-sm font-medium text-foreground">Failed to load dashboard</p>
        <p className="text-xs text-muted-foreground">{error.message}</p>
        <Button size="sm" onClick={reset}>Try again</Button>
      </div>
    </PageContainer>
  )
}
