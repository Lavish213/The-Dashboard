'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Share2, Users, FileText, TrendingUp } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

interface SocialStats {
  total_posts: number
  posted: number
  total_leads_generated: number
  by_platform: Record<string, number>
}

export function SocialWidget() {
  const stats = useQuery({ queryKey: ['social-summary'], queryFn: ({ signal }) => apiFetch<SocialStats>('/api/v1/social/posts/analytics', { signal }), refetchInterval: 60_000, retry: 1 })
  const leads = useQuery({ queryKey: ['social-lead-count'], queryFn: ({ signal }) => apiFetch<{ total: number }>('/api/v1/social/leads?page_size=1', { signal }), refetchInterval: 60_000, retry: 1 })
  const reddit = useQuery({ queryKey: ['reddit-match-count'], queryFn: ({ signal }) => apiFetch<{ total: number }>('/api/v1/reddit/matches?page_size=1', { signal }), refetchInterval: 60_000, retry: 1 })
  const failed = stats.isError || leads.isError || reddit.isError
  const loading = stats.isPending || leads.isPending || reddit.isPending
  const tiles = [
    { label: 'Posts queued', value: stats.data ? Math.max(0, stats.data.total_posts - stats.data.posted) : null, icon: FileText },
    { label: 'Posts live', value: stats.data?.posted ?? null, icon: Share2 },
    { label: 'Social leads', value: leads.data?.total ?? null, icon: Users },
    { label: 'Reddit matches', value: reddit.data?.total ?? null, icon: TrendingUp },
  ]

  return (
    <section className="rounded-lg border bg-card p-5 space-y-4" aria-labelledby="social-heading" aria-busy={loading}>
      <div className="flex items-center justify-between gap-3">
        <h2 id="social-heading" className="text-base font-semibold">Social activity</h2>
        <Link href="/social" className="text-sm text-foreground underline underline-offset-4">View social</Link>
      </div>
      {failed && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-destructive/30 bg-destructive/5 p-3">
        <p className="text-sm text-destructive">Social data unavailable. Existing values may be stale; — means unavailable.</p>
        <Button size="sm" variant="outline" disabled={stats.isFetching || leads.isFetching || reddit.isFetching} onClick={() => { void stats.refetch(); void leads.refetch(); void reddit.refetch() }}>Retry social data</Button>
      </div>}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {tiles.map(tile => <div key={tile.label} className="rounded-md bg-muted/40 p-3">
          <tile.icon className="h-4 w-4 mb-2 text-muted-foreground" aria-hidden="true" />
          <p className="text-2xl font-semibold tabular-nums">{tile.value ?? (loading ? '…' : '—')}</p>
          <p className="text-xs text-muted-foreground mt-1">{tile.label}</p>
        </div>)}
      </div>
      {stats.data && Object.keys(stats.data.by_platform).length > 0 && <div className="flex flex-wrap gap-3 border-t border-border pt-3">
        {Object.entries(stats.data.by_platform).map(([platform, count]) => <span key={platform} className="text-xs text-muted-foreground">{platform}: <span className="text-foreground font-medium">{count}</span></span>)}
      </div>}
    </section>
  )
}
