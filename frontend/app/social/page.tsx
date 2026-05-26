'use client'

import { useEffect, useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { apiFetch } from '@/services/api'
import { toast } from 'sonner'
import {
  Share2, MessageSquare, Radio, BarChart2,
  Plus, Clock, CheckCircle2, AlertCircle,
  ExternalLink, UserPlus, Loader2
} from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SocialPost {
  id: string
  platform: string
  content: string
  spintax_variants: string[] | null
  target_group: string | null
  status: string
  post_type: string | null
  scheduled_at: string | null
  posted_at: string | null
  comments_count: number
  leads_generated: number
  created_at: string
}

interface SocialLead {
  id: string
  full_name: string | null
  phone: string | null
  platform: string
  message: string | null
  intent_score: number | null
  intent_label: string | null
  status: string
  lead_id: string | null
  created_at: string
}

interface RedditMatch {
  id: string
  subreddit: string
  title: string
  body: string | null
  url: string
  author: string | null
  intent_score: number
  intent_label: string
  status: string
  created_at: string
}

interface Analytics {
  total_posts: number
  posted: number
  total_leads_generated: number
  by_platform: Record<string, number>
}

type Tab = 'queue' | 'compose' | 'leads' | 'reddit' | 'analytics'

const PLATFORM_COLORS: Record<string, string> = {
  facebook: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  instagram: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  reddit: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  marketplace: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground border-border',
  queued: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  ready: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  posted: 'bg-green-500/10 text-green-400 border-green-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
}

const INTENT_COLORS: Record<string, string> = {
  hot: 'bg-red-500/10 text-red-400 border-red-500/20',
  warm: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  cold: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export default function SocialPage() {
  const [tab, setTab] = useState<Tab>('queue')
  const [posts, setPosts] = useState<SocialPost[]>([])
  const [leads, setLeads] = useState<SocialLead[]>([])
  const [redditMatches, setRedditMatches] = useState<RedditMatch[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [composing, setComposing] = useState(false)
  const [curatorInput, setCuratorInput] = useState('')
  const [curatorType, setCuratorType] = useState('text')
  const [curatorVariants, setCuratorVariants] = useState<string[]>([])
  const [curatorLoading, setCuratorLoading] = useState(false)
  const [selectedVariant, setSelectedVariant] = useState<string>('')
  const [postPlatform, setPostPlatform] = useState('facebook')
  const [postGroup, setPostGroup] = useState('')
  const [savingPost, setSavingPost] = useState(false)
  const [scanning, setScanning] = useState(false)

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    setLoading(true)
    try {
      const [postsData, leadsData, redditData, analyticsData] = await Promise.all([
        apiFetch<{ items: SocialPost[] }>('/api/v1/social/posts?page_size=50'),
        apiFetch<{ items: SocialLead[] }>('/api/v1/social/leads?page_size=50'),
        apiFetch<{ items: RedditMatch[] }>('/api/v1/reddit/matches?page_size=50'),
        apiFetch<Analytics>('/api/v1/social/posts/analytics'),
      ])
      setPosts(postsData.items)
      setLeads(leadsData.items)
      setRedditMatches(redditData.items)
      setAnalytics(analyticsData)
    } catch {
      toast.error('Failed to load social data')
    } finally {
      setLoading(false)
    }
  }

  async function handleCurate() {
    if (!curatorInput.trim()) return
    setCuratorLoading(true)
    setCuratorVariants([])
    try {
      const data = await apiFetch<{ variants: string[] }>('/api/v1/curator/process', {
        method: 'POST',
        body: JSON.stringify({ type: curatorType, content: curatorInput }),
      })
      setCuratorVariants(data.variants)
      setSelectedVariant(data.variants[0] || '')
      toast.success('3 variants generated')
    } catch {
      toast.error('Curator failed')
    } finally {
      setCuratorLoading(false)
    }
  }

  async function handleSavePost() {
    if (!selectedVariant.trim()) return
    setSavingPost(true)
    try {
      await apiFetch('/api/v1/social/posts', {
        method: 'POST',
        body: JSON.stringify({
          platform: postPlatform,
          content: selectedVariant,
          spintax_variants: curatorVariants,
          target_group: postGroup || null,
          status: 'queued',
          post_type: 'curator',
          source_url: curatorType !== 'text' ? curatorInput : null,
        }),
      })
      toast.success('Post added to queue')
      setCuratorInput('')
      setCuratorVariants([])
      setSelectedVariant('')
      setTab('queue')
      loadAll()
    } catch {
      toast.error('Failed to save post')
    } finally {
      setSavingPost(false)
    }
  }

  async function handleConvertLead(lead: SocialLead) {
    try {
      const data = await apiFetch<{ lead_id: string }>(`/api/v1/social/leads/${lead.id}/convert`, {
        method: 'PATCH',
        body: JSON.stringify({}),
      })
      toast.success(`Lead created — Sophia will call`)
      setLeads(prev => prev.map(l => l.id === lead.id ? { ...l, status: 'converted', lead_id: data.lead_id } : l))
    } catch {
      toast.error('Failed to convert lead')
    }
  }

  async function handleScan() {
    setScanning(true)
    try {
      const data = await apiFetch<{ new_matches: number }>('/api/v1/reddit/matches/scan', { method: 'POST' })
      toast.success(`Scan complete — ${data.new_matches} new matches`)
      loadAll()
    } catch {
      toast.error('Reddit scan failed — check API credentials')
    } finally {
      setScanning(false)
    }
  }

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'queue', label: 'Queue', count: posts.filter(p => p.status === 'queued' || p.status === 'ready').length },
    { id: 'compose', label: 'Compose' },
    { id: 'leads', label: 'Leads', count: leads.filter(l => l.status === 'new').length },
    { id: 'reddit', label: 'Reddit', count: redditMatches.filter(m => m.intent_label === 'hot').length },
    { id: 'analytics', label: 'Analytics' },
  ]

  return (
    <PageContainer title="Social" description="Content queue, lead capture, and group intelligence">
      <div className="space-y-4 max-w-content">
        <div className="flex items-center gap-2 border-b border-border pb-3 flex-wrap">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === t.id
                  ? 'bg-teal-500/10 text-teal-400 border border-teal-500/25'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t.label}
              {t.count != null && t.count > 0 && (
                <span className="rounded-full bg-teal-500/20 px-1.5 py-0.5 text-xs tabular-nums text-teal-400">
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {tab === 'queue' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">{posts.length} total posts</p>
              <Button size="sm" onClick={() => setTab('compose')} className="gap-2 h-8 bg-teal-500/10 text-teal-400 border border-teal-500/25 hover:bg-teal-500/20">
                <Plus className="h-3.5 w-3.5" /> New post
              </Button>
            </div>
            {loading ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => <div key={i} className="h-20 rounded-lg border bg-card animate-pulse" />)}
              </div>
            ) : posts.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-10 text-center">
                <Share2 className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-40" />
                <p className="text-sm text-muted-foreground">No posts yet</p>
                <p className="text-xs text-muted-foreground mt-1">Use the Compose tab to create your first post</p>
              </div>
            ) : (
              posts.map(post => (
                <div key={post.id} className="rounded-lg border bg-card shadow-card p-4 space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`rounded border px-2 py-0.5 text-xs font-medium ${PLATFORM_COLORS[post.platform] ?? 'bg-muted text-muted-foreground border-border'}`}>
                        {post.platform}
                      </span>
                      <span className={`rounded border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[post.status] ?? 'bg-muted text-muted-foreground border-border'}`}>
                        {post.status}
                      </span>
                      {post.target_group && (
                        <span className="text-xs text-muted-foreground">{post.target_group}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0 text-xs text-muted-foreground">
                      {post.leads_generated > 0 && (
                        <span className="text-green-400 font-medium">{post.leads_generated} leads</span>
                      )}
                      {post.scheduled_at && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(post.scheduled_at)}
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-foreground line-clamp-2">{post.content}</p>
                  <p className="text-xs text-muted-foreground">{formatDate(post.created_at)}</p>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'compose' && (
          <div className="space-y-4 max-w-2xl">
            <div className="rounded-lg border bg-card shadow-card p-4 space-y-4">
              <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Curator — drop a link or idea</p>
              <div className="flex gap-2">
                {(['text', 'url', 'tiktok', 'instagram', 'youtube'].map(t => (
                  <button
                    key={t}
                    onClick={() => setCuratorType(t)}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                      curatorType === t
                        ? 'bg-teal-500/15 text-teal-400 border border-teal-500/25'
                        : 'text-muted-foreground hover:text-foreground border border-transparent'
                    }`}
                  >
                    {t}
                  </button>
                )))}
              </div>
              <textarea
                value={curatorInput}
                onChange={e => setCuratorInput(e.target.value)}
                placeholder={curatorType === 'text'
                  ? 'Type an idea, topic, or paste raw text...'
                  : 'Paste a URL...'
                }
                rows={3}
                className="w-full rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-1 focus:ring-teal-500/50"
              />
              <Button
                onClick={handleCurate}
                disabled={curatorLoading || !curatorInput.trim()}
                className="bg-teal-500/15 text-teal-400 border border-teal-500/25 hover:bg-teal-500/25 gap-2"
                size="sm"
              >
                {curatorLoading ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Generating…</> : '✨ Generate 3 variants'}
              </Button>
            </div>

            {curatorVariants.length > 0 && (
              <div className="rounded-lg border bg-card shadow-card p-4 space-y-3">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Pick a variant</p>
                {curatorVariants.map((v, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedVariant(v)}
                    className={`w-full text-left rounded-md border p-3 text-sm transition-all ${
                      selectedVariant === v
                        ? 'border-teal-500/30 bg-teal-500/5 text-foreground'
                        : 'border-border bg-muted/20 text-muted-foreground hover:text-foreground hover:border-border/80'
                    }`}
                  >
                    <span className="text-xs text-muted-foreground mr-2">#{i + 1}</span>
                    {v}
                  </button>
                ))}

                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
                  <div>
                    <label className="text-xs text-muted-foreground">Platform</label>
                    <select
                      value={postPlatform}
                      onChange={e => setPostPlatform(e.target.value)}
                      className="w-full mt-1 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-teal-500/50"
                    >
                      <option value="facebook">Facebook</option>
                      <option value="instagram">Instagram</option>
                      <option value="marketplace">Marketplace</option>
                      <option value="reddit">Reddit</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Target group (optional)</label>
                    <input
                      type="text"
                      value={postGroup}
                      onChange={e => setPostGroup(e.target.value)}
                      placeholder="e.g. Stockton Homeowners"
                      className="w-full mt-1 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-teal-500/50"
                    />
                  </div>
                </div>

                <Button
                  onClick={handleSavePost}
                  disabled={savingPost || !selectedVariant.trim()}
                  className="w-full bg-teal-500/15 text-teal-400 border border-teal-500/25 hover:bg-teal-500/25"
                  size="sm"
                >
                  {savingPost ? 'Saving…' : '+ Add to queue'}
                </Button>
              </div>
            )}
          </div>
        )}

        {tab === 'leads' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">{leads.length} social leads</p>
            </div>
            {loading ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => <div key={i} className="h-20 rounded-lg border bg-card animate-pulse" />)}
              </div>
            ) : leads.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-10 text-center">
                <MessageSquare className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-40" />
                <p className="text-sm text-muted-foreground">No social leads yet</p>
                <p className="text-xs text-muted-foreground mt-1">Leads from Facebook comments, Instagram DMs, and Reddit appear here</p>
              </div>
            ) : (
              leads.map(lead => (
                <div key={lead.id} className="rounded-lg border bg-card shadow-card p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{lead.full_name ?? 'Unknown'}</p>
                      {lead.phone && <p className="text-xs text-muted-foreground font-mono">{lead.phone}</p>}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className={`rounded border px-2 py-0.5 text-xs font-medium ${PLATFORM_COLORS[lead.platform] ?? 'bg-muted text-muted-foreground border-border'}`}>
                        {lead.platform}
                      </span>
                      {lead.intent_label && (
                        <span className={`rounded border px-2 py-0.5 text-xs font-medium ${INTENT_COLORS[lead.intent_label] ?? 'bg-muted text-muted-foreground border-border'}`}>
                          {lead.intent_label}
                        </span>
                      )}
                    </div>
                  </div>
                  {lead.message && (
                    <p className="text-xs text-muted-foreground line-clamp-2 bg-muted/30 rounded px-3 py-2">
                      "{lead.message}"
                    </p>
                  )}
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">{formatDate(lead.created_at)}</p>
                    {lead.lead_id ? (
                      <span className="flex items-center gap-1 text-xs text-green-400">
                        <CheckCircle2 className="h-3.5 w-3.5" /> In pipeline
                      </span>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleConvertLead(lead)}
                        className="h-7 gap-1.5 bg-teal-500/10 text-teal-400 border border-teal-500/20 hover:bg-teal-500/20 text-xs"
                      >
                        <UserPlus className="h-3 w-3" /> Create lead → Sophia
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'reddit' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">{redditMatches.length} keyword matches</p>
              <Button
                size="sm"
                onClick={handleScan}
                disabled={scanning}
                className="gap-2 h-8 bg-teal-500/10 text-teal-400 border border-teal-500/25 hover:bg-teal-500/20"
              >
                {scanning ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Scanning…</> : <><Radio className="h-3.5 w-3.5" /> Scan now</>}
              </Button>
            </div>
            {redditMatches.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-10 text-center">
                <Radio className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-40" />
                <p className="text-sm text-muted-foreground">No Reddit matches yet</p>
                <p className="text-xs text-muted-foreground mt-1">Add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to .env then click Scan</p>
              </div>
            ) : (
              redditMatches.map(match => (
                <div key={match.id} className={`rounded-lg border shadow-card p-4 space-y-2 ${
                  match.intent_label === 'hot'
                    ? 'border-red-500/20 bg-red-500/5'
                    : match.intent_label === 'warm'
                    ? 'border-amber-500/20 bg-amber-500/5'
                    : 'border-border bg-card'
                }`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-muted-foreground">r/{match.subreddit}</span>
                      <span className={`rounded border px-2 py-0.5 text-xs font-medium ${INTENT_COLORS[match.intent_label] ?? 'bg-muted text-muted-foreground border-border'}`}>
                        {match.intent_label} · {match.intent_score}
                      </span>
                    </div>
                    <a
                      href={match.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-teal-400 transition-colors flex-shrink-0"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                  <p className="text-sm font-medium text-foreground">{match.title}</p>
                  {match.body && (
                    <p className="text-xs text-muted-foreground line-clamp-2">{match.body}</p>
                  )}
                  <p className="text-xs text-muted-foreground">by u/{match.author} · {formatDate(match.created_at)}</p>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'analytics' && (
          <div className="space-y-4">
            {analytics && (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-lg border bg-card shadow-card p-4 text-center">
                    <p className="text-2xl font-semibold tabular-nums text-foreground">{analytics.total_posts}</p>
                    <p className="text-xs text-muted-foreground mt-1">Total posts</p>
                  </div>
                  <div className="rounded-lg border bg-card shadow-card p-4 text-center">
                    <p className="text-2xl font-semibold tabular-nums text-green-400">{analytics.posted}</p>
                    <p className="text-xs text-muted-foreground mt-1">Posted</p>
                  </div>
                  <div className="rounded-lg border bg-card shadow-card p-4 text-center">
                    <p className="text-2xl font-semibold tabular-nums text-teal-400">{analytics.total_leads_generated}</p>
                    <p className="text-xs text-muted-foreground mt-1">Leads generated</p>
                  </div>
                  <div className="rounded-lg border bg-card shadow-card p-4 text-center">
                    <p className="text-2xl font-semibold tabular-nums text-foreground">{leads.length}</p>
                    <p className="text-xs text-muted-foreground mt-1">Social leads</p>
                  </div>
                </div>
                {Object.keys(analytics.by_platform).length > 0 && (
                  <div className="rounded-lg border bg-card shadow-card p-4 space-y-3">
                    <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">By platform</p>
                    {Object.entries(analytics.by_platform).map(([platform, count]) => (
                      <div key={platform} className="flex items-center justify-between">
                        <span className={`rounded border px-2 py-0.5 text-xs font-medium ${PLATFORM_COLORS[platform] ?? 'bg-muted text-muted-foreground border-border'}`}>
                          {platform}
                        </span>
                        <span className="text-sm tabular-nums text-foreground">{count} posts</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </PageContainer>
  )
}
