'use client'

import { PageContainer } from '@/components/workspace/PageContainer'
import { Share2, Instagram, MessageSquare, Radio, BarChart2 } from 'lucide-react'

function ComingSoonCard({ icon: Icon, title, description, badge }: {
  icon: any
  title: string
  description: string
  badge?: string
}) {
  return (
    <div className="rounded-lg border bg-card shadow-card p-5 space-y-3">
      <div className="flex items-start justify-between">
        <div className="h-9 w-9 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
          <Icon className="h-4 w-4 text-teal-400" />
        </div>
        {badge && (
          <span className="rounded border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400 font-medium">
            {badge}
          </span>
        )}
      </div>
      <div>
        <p className="text-sm font-semibold text-foreground font-display">{title}</p>
        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{description}</p>
      </div>
    </div>
  )
}

export default function SocialPage() {
  return (
    <PageContainer
      title="Social"
      description="Content queue, lead capture, and group intelligence"
    >
      <div className="space-y-6 max-w-content">
        <div className="rounded-lg border border-teal-500/20 bg-teal-500/5 p-5 shadow-card">
          <div className="flex items-center gap-3 mb-2">
            <div className="h-8 w-8 rounded-lg bg-teal-500/15 border border-teal-500/25 flex items-center justify-center">
              <Share2 className="h-4 w-4 text-teal-400" />
            </div>
            <p className="text-sm font-semibold text-foreground font-display">
              Social Command Center
            </p>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Full social automation coming in batch 13-27. Facebook group posting,
            Instagram comment-to-DM, Reddit monitoring, content curator, and unified lead inbox —
            all feeding directly into Sophia's call pipeline.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <ComingSoonCard
            icon={Share2}
            title="Content Queue"
            description="Write once, post everywhere. AI generates spintax variants in your voice. You approve, Playwright posts."
            badge="Batch 22"
          />
          <ComingSoonCard
            icon={MessageSquare}
            title="Curator"
            description="Drop a TikTok link, news article, or idea. AI rewrites it as a Facebook group post in your voice with 3 variants."
            badge="Batch 15"
          />
          <ComingSoonCard
            icon={Instagram}
            title="Instagram Leads"
            description="Comment OFFER → InstantDM fires → lead created → Sophia calls. Meta-approved, zero ban risk."
            badge="Batch 17"
          />
          <ComingSoonCard
            icon={Radio}
            title="Reddit Monitor"
            description="PRAW watches r/Stockton and 9 other subreddits 24/7. Keyword matches surface here — you reply manually."
            badge="Batch 14"
          />
          <ComingSoonCard
            icon={BarChart2}
            title="Social Analytics"
            description="Track which post type generates the most leads. Posts this week, leads from social, best performing platform."
            badge="Batch 25"
          />
          <ComingSoonCard
            icon={Share2}
            title="Unified Inbox"
            description="Facebook comments, Instagram DMs, Reddit mentions — all scored for intent in one feed. One-click to create lead."
            badge="Batch 21"
          />
        </div>
      </div>
    </PageContainer>
  )
}