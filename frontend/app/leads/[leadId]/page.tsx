'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { PageContainer } from '@/components/workspace/PageContainer'
import { LeadAvatar } from '@/components/leads/LeadAvatar'
import { apiFetch } from '@/services/api'
import { toast } from 'sonner'
import { scoreColor, STATUS_COLORS } from '@/constants/colors'
import { ArrowLeft, Phone, Mail, MapPin, Calendar, FileText, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Lead {
  id: string
  full_name: string
  phone: string | null
  email: string | null
  lead_status: string
  lead_source: string | null
  ai_score: number | null
  address: string | null
  city: string | null
  state: string | null
  notes: string | null
  follow_up_at: string | null
  last_contacted_at: string | null
  created_at: string
}

interface Call {
  id: string
  provider_call_id: string
  call_status: string
  duration_seconds: number | null
  created_at: string
}

interface Note {
  id: string
  content: string
  created_at: string
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function formatDuration(s: number | null): string {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

function InfoRow({ icon: Icon, label, value }: { icon: any; label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-3">
      <Icon className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm text-foreground">{value}</p>
      </div>
    </div>
  )
}

export default function LeadDetailPage() {
  const { leadId } = useParams<{ leadId: string }>()
  const router = useRouter()
  const [lead, setLead] = useState<Lead | null>(null)
  const [calls, setCalls] = useState<Call[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [newNote, setNewNote] = useState('')
  const [addingNote, setAddingNote] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [leadData, callsData] = await Promise.all([
          apiFetch<Lead>(`/api/v1/leads/${leadId}`),
          apiFetch<{ items: Call[] }>(`/api/v1/calls?lead_id=${leadId}&page_size=10`),
        ])
        setLead(leadData)
        setCalls(callsData.items)
      } catch {
        toast.error('Failed to load lead')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [leadId])

  async function handleAddNote() {
    if (!newNote.trim()) return
    setAddingNote(true)
    try {
      const note = await apiFetch<Note>(`/api/v1/leads/${leadId}/notes`, {
        method: 'POST',
        body: JSON.stringify({ content: newNote.trim() }),
      })
      setNotes((prev) => [note, ...prev])
      setNewNote('')
      toast.success('Note added')
    } catch {
      toast.error('Failed to add note')
    } finally {
      setAddingNote(false)
    }
  }

  if (loading) {
    return (
      <PageContainer title="Lead Detail">
        <div className="space-y-4 max-w-3xl">
          <div className="h-32 rounded-lg border bg-card animate-pulse" />
          <div className="h-48 rounded-lg border bg-card animate-pulse" />
        </div>
      </PageContainer>
    )
  }

  if (!lead) {
    return (
      <PageContainer title="Lead not found">
        <p className="text-sm text-muted-foreground">This lead doesn't exist or was deleted.</p>
      </PageContainer>
    )
  }

  const sc = scoreColor(lead.ai_score)
  const statusCls = STATUS_COLORS[lead.lead_status] ?? 'bg-muted text-muted-foreground border-border'
  const address = [lead.address, lead.city, lead.state].filter(Boolean).join(', ')

  return (
    <PageContainer title={lead.full_name} description="Lead detail">
      <div className="max-w-3xl space-y-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.back()}
          className="gap-2 text-muted-foreground hover:text-foreground -ml-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <div className="rounded-lg border bg-card shadow-card p-5 space-y-4">
          <div className="flex items-start gap-4">
            <LeadAvatar name={lead.full_name} score={lead.ai_score} size="lg" />
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <h1 className="text-lg font-semibold text-foreground font-display">
                    {lead.full_name}
                  </h1>
                  {lead.lead_source && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Source: {lead.lead_source}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`rounded border px-2 py-0.5 text-xs font-medium ${statusCls}`}>
                    {lead.lead_status}
                  </span>
                  {lead.ai_score != null && (
                    <span className={`text-sm font-semibold tabular-nums ${sc.text}`}>
                      Score {lead.ai_score}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 pt-2 border-t border-border">
            <InfoRow icon={Phone} label="Phone" value={lead.phone} />
            <InfoRow icon={Mail} label="Email" value={lead.email} />
            <InfoRow icon={MapPin} label="Address" value={address || null} />
            <InfoRow icon={Calendar} label="Created" value={formatDate(lead.created_at)} />
            {lead.follow_up_at && (
              <InfoRow icon={Clock} label="Follow up" value={formatDate(lead.follow_up_at)} />
            )}
            {lead.last_contacted_at && (
              <InfoRow icon={Phone} label="Last contact" value={formatDate(lead.last_contacted_at)} />
            )}
          </div>
        </div>

        <div className="rounded-lg border bg-card shadow-card p-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Call history
          </p>
          {calls.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">No calls yet</p>
          ) : (
            <div className="space-y-2">
              {calls.map((call) => (
                <div
                  key={call.id}
                  className="flex items-center gap-3 rounded-md border border-border bg-muted/30 px-3 py-2"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono text-muted-foreground truncate">
                      {call.provider_call_id.slice(0, 16)}…
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {formatDate(call.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`rounded border px-2 py-0.5 text-xs ${STATUS_COLORS[call.call_status] ?? 'bg-muted text-muted-foreground border-border'}`}>
                      {call.call_status}
                    </span>
                    <span className="text-xs text-muted-foreground tabular-nums font-mono">
                      {formatDuration(call.duration_seconds)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-lg border bg-card shadow-card p-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Notes
          </p>
          <div className="space-y-2">
            <textarea
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              placeholder="Add a note about this lead…"
              rows={3}
              className="w-full rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <Button
              size="sm"
              onClick={handleAddNote}
              disabled={addingNote || !newNote.trim()}
              className="bg-teal-500/15 text-teal-400 border border-teal-500/25 hover:bg-teal-500/25"
            >
              {addingNote ? 'Saving…' : 'Add note'}
            </Button>
          </div>
          {notes.length === 0 && lead.notes && (
            <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
              <p className="text-sm text-foreground">{lead.notes}</p>
            </div>
          )}
          {notes.map((note) => (
            <div key={note.id} className="rounded-md border border-border bg-muted/30 px-3 py-2 space-y-1">
              <p className="text-sm text-foreground">{note.content}</p>
              <p className="text-xs text-muted-foreground">{formatDate(note.created_at)}</p>
            </div>
          ))}
        </div>
      </div>
    </PageContainer>
  )
}