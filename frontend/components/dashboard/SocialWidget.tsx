'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/services/api'
import { Share2, Users, FileText, TrendingUp } from 'lucide-react'
import Link from 'next/link'

interface SocialStats {
  total_posts: number
  posted: number
  total_leads_generated: number
  by_platform: Record<string, number>
}

interface SocialLeadCount {
  total: number
}

interface RedditCount {
  total: number
}

export function SocialWidget() {
  const [stats, setStats] = useState<SocialStats | null>(null)
  const [leadCount, setLeadCount] = useState(0)
  const [redditCount, setRedditCount] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [s, l, r] = await Promise.all([
          apiFetch<SocialStats>('/api/v1/social/posts/analytics'),
          apiFetch<SocialLeadCount>('/api/v1/social/leads?page_size=1'),
          apiFetch<RedditCount>('/api/v1/reddit/matches?page_size=1'),
        ])
        setStats(s)
        setLeadCount((l as any).total ?? 0)
        setRedditCount((r as any).total ?? 0)
      } catch {}
      finally { setLoading(false) }
    }
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [])

  const tiles = [
    { label: 'Posts queued', value: stats ? stats.total_posts - stats.posted : 0, icon: FileText, color: 'text-blue-400' },
    { label: 'Posts live', value: stats?.posted ?? 0, icon: Share2, color: 'text-green-400' },
    { label: 'Social leads', value: leadCount, icon: Users, color: 'text-teal-400' },
    { label: 'Reddit matches', value: redditCount, icon: TrendingUp, color: 'text-orange-400' },
  ]

  return (
    <div className="rounded-lg border bg-card shadow-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Share2 className="h-4 w-4 text-teal-400" />
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Social</p>
        </div>
        <Link href="/social" className="text-xs text-teal-400 hover:underline">View all</Link>
      </div>
      {loading ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 rounded-md bg-muted animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {tiles.map(t => (
            <div key={t.label} className="rounded-md bg-muted/40 p-3 text-center">
              <t.icon className={`h-4 w-4 mx-auto mb-1 ${t.color}`} />
              <p className={`text-xl font-semibold tabular-nums ${t.color}`}>{t.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{t.label}</p>
            </div>
          ))}
        </div>
      )}
      {stats && Object.keys(stats.by_platform).length > 0 && (
        <div className="flex items-center gap-3 pt-1 border-t border-border">
          {Object.entries(stats.by_platform).map(([platform, count]) => (
            <span key={platform} className="text-xs text-muted-foreground">
              {platform}: <span className="text-foreground font-medium">{count}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
