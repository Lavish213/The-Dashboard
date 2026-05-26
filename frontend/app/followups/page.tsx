'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { PageContainer } from '@/components/workspace/PageContainer'
import { apiFetch } from '@/services/api'
import { toast } from 'sonner'
import { LeadAvatar } from '@/components/leads/LeadAvatar'
import { STATUS_COLORS } from '@/constants/colors'
import { Bell, AlertCircle, Clock, CheckCircle2 } from 'lucide-react'

interface Lead {
  id: string
  full_name: string
  phone: string | null
  lead_status: string
  ai_score: number | null
  follow_up_at: string | null
  notes: string | null
  created_at: string
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function isOverdue(date: string) {
  return new Date(date) < new Date()
}

function isToday(date: string) {
  const d = new Date(date)
  const now = new Date()
  return d.toDateString() === now.toDateString()
}

function FollowUpCard({ lead, onClick }: { lead: Lead; onClick: () => void }) {
  const overdue = lead.follow_up_at && isOverdue(lead.follow_up_at)
  const today = lead.follow_up_at && isToday(lead.follow_up_at)

  return (
    <div
      onClick={onClick}
      className={`rounded-lg border p-4 cursor-pointer transition-all hover:shadow-card-hover space-y-3 ${
        overdue
          ? 'border-red-500/25 bg-red-500/5 hover:border-red-500/40'
          : today
          ? 'border-amber-500/25 bg-amber-500/5 hover:border-amber-500/40'
          : 'border-border bg-card hover:border-border/80'
      }`}
    >
      <div className="flex items-start gap-3">
        <LeadAvatar name={lead.full_name} score={lead.ai_score} size="sm" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground truncate">{lead.full_name}</p>
          {lead.phone && (
            <p className="text-xs text-muted-foreground font-mono mt-0.5">{lead.phone}</p>
          )}
        </div>
        {overdue ? (
          <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
        ) : today ? (
          <Bell className="h-4 w-4 text-amber-400 flex-shrink-0" />
        ) : (
          <Clock className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        )}
      </div>

      <div className="flex items-center justify-between">
        <span className={`rounded border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[lead.lead_status] ?? 'bg-muted text-muted-foreground border-border'}`}>
          {lead.lead_status}
        </span>
        {lead.follow_up_at && (
          <span className={`text-xs font-medium tabular-nums ${
            overdue ? 'text-red-400' : today ? 'text-amber-400' : 'text-muted-foreground'
          }`}>
            {overdue ? 'Overdue · ' : today ? 'Today · ' : ''}{formatDate(lead.follow_up_at)}
          </span>
        )}
      </div>

      {lead.notes && (
        <p className="text-xs text-muted-foreground line-clamp-2 pt-1 border-t border-border">
          {lead.notes.split('\n')[0].replace(/^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] /, '')}
        </p>
      )}
    </div>
  )
}

export default function FollowupsPage() {
  const router = useRouter()
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch<{ items: Lead[] }>(
          '/api/v1/leads?page_size=200'
        )
        const withFollowup = data.items.filter(l => l.follow_up_at)
        withFollowup.sort((a, b) =>
          new Date(a.follow_up_at!).getTime() - new Date(b.follow_up_at!).getTime()
        )
        setLeads(withFollowup)
      } catch {
        toast.error('Failed to load follow-ups')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const overdue = leads.filter(l => l.follow_up_at && isOverdue(l.follow_up_at) && !isToday(l.follow_up_at))
  const today = leads.filter(l => l.follow_up_at && isToday(l.follow_up_at))
  const upcoming = leads.filter(l => l.follow_up_at && !isOverdue(l.follow_up_at) && !isToday(l.follow_up_at))

  return (
    <PageContainer title="Follow-ups" description="Scheduled callbacks and follow-up queue">
      <div className="space-y-6 max-w-content">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 text-center shadow-card">
            <p className="text-2xl font-semibold tabular-nums text-red-400">{overdue.length}</p>
            <p className="text-xs text-muted-foreground mt-1">Overdue</p>
          </div>
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-center shadow-card">
            <p className="text-2xl font-semibold tabular-nums text-amber-400">{today.length}</p>
            <p className="text-xs text-muted-foreground mt-1">Due today</p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-center shadow-card">
            <p className="text-2xl font-semibold tabular-nums text-foreground">{upcoming.length}</p>
            <p className="text-xs text-muted-foreground mt-1">Upcoming</p>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-24 rounded-lg border bg-card animate-pulse" />
            ))}
          </div>
        ) : leads.length === 0 ? (
          <div className="rounded-lg border bg-card p-10 text-center shadow-card">
            <CheckCircle2 className="h-8 w-8 text-teal-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-foreground">All caught up</p>
            <p className="text-xs text-muted-foreground mt-1">
              No follow-ups scheduled. Set follow-up dates on lead detail pages.
            </p>
          </div>
        ) : (
          <>
            {overdue.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-widest text-red-400">
                  Overdue — {overdue.length}
                </p>
                {overdue.map(lead => (
                  <FollowUpCard key={lead.id} lead={lead} onClick={() => router.push(`/leads/${lead.id}`)} />
                ))}
              </div>
            )}
            {today.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-widest text-amber-400">
                  Today — {today.length}
                </p>
                {today.map(lead => (
                  <FollowUpCard key={lead.id} lead={lead} onClick={() => router.push(`/leads/${lead.id}`)} />
                ))}
              </div>
            )}
            {upcoming.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Upcoming — {upcoming.length}
                </p>
                {upcoming.map(lead => (
                  <FollowUpCard key={lead.id} lead={lead} onClick={() => router.push(`/leads/${lead.id}`)} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </PageContainer>
  )
}