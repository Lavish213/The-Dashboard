'use client'

import { useEffect, useState } from 'react'
import { useQueryState, parseAsString } from 'nuqs'
import { PageContainer } from '@/components/workspace/PageContainer'
import { apiFetch } from '@/services/api'

type WorkflowStatus = 'pending' | 'active' | 'paused' | 'completed' | 'failed' | 'cancelled'

interface Workflow {
  id: string
  workflow_type: string
  workflow_status: WorkflowStatus
  current_step: string | null
  lead_id: string | null
  created_at: string
}

interface WorkflowEvent {
  id: string
  event_type: string
  payload: Record<string, unknown>
  actor_type: string
  created_at: string
}

const STATUS_COLORS: Record<WorkflowStatus, string> = {
  pending: 'bg-muted text-muted-foreground border-border',
  active: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  paused: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  completed: 'bg-green-500/10 text-green-400 border-green-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  cancelled: 'bg-muted text-muted-foreground border-border',
}

const STATUSES = [
  { value: '', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'completed', label: 'Completed' },
  { value: 'paused', label: 'Paused' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
]

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [events, setEvents] = useState<WorkflowEvent[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useQueryState('status', parseAsString.withDefault(''))

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ page_size: '100' })
    if (statusFilter) params.set('workflow_status', statusFilter)
    apiFetch<{ items: Workflow[] }>(`/api/v1/workflows?${params}`)
      .then((r) => setWorkflows(r.items ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [statusFilter])

  async function loadEvents(id: string) {
    setSelected(id)
    setEventsLoading(true)
    try {
      const result = await apiFetch<WorkflowEvent[]>(`/api/v1/workflows/${id}/events`)
      setEvents(Array.isArray(result) ? result : [])
    } catch {
      setEvents([])
    } finally {
      setEventsLoading(false)
    }
  }

  const selectedWorkflow = workflows.find((w) => w.id === selected)

  return (
    <PageContainer title="Workflows" description="Lead acquisition workflow execution">
      <div className="flex gap-1.5 mb-4 flex-wrap">
        {STATUSES.map((s) => (
          <button
            key={s.value}
            onClick={() => setStatusFilter(s.value)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              statusFilter === s.value
                ? 'border-teal-500/30 bg-teal-500/10 text-teal-400'
                : 'border-border text-muted-foreground hover:text-foreground'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground px-1">
            {workflows.length} workflows
          </p>
          {loading && [...Array(4)].map((_, i) => (
            <div key={i} className="rounded-lg border bg-card p-4 h-20 animate-pulse" />
          ))}
          {!loading && workflows.length === 0 && (
            <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              No workflows found
            </div>
          )}
          {!loading && workflows.map((wf) => (
            <button
              key={wf.id}
              onClick={() => loadEvents(wf.id)}
              className={`w-full text-left rounded-lg border p-3 transition-colors hover:bg-muted/30 ${selected === wf.id ? 'border-teal-500/30 bg-teal-500/5' : 'bg-card'}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{wf.workflow_type.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-muted-foreground mt-0.5 font-mono">{wf.id.slice(0, 8)}…</p>
                </div>
                <span className={`flex-shrink-0 rounded border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[wf.workflow_status]}`}>
                  {wf.workflow_status}
                </span>
              </div>
              {wf.current_step && (
                <p className="text-xs text-muted-foreground mt-2">Step: <span className="text-foreground">{wf.current_step}</span></p>
              )}
              <p className="text-xs text-muted-foreground mt-1">{new Date(wf.created_at).toLocaleString()}</p>
            </button>
          ))}
        </div>

        <div>
          {!selected && (
            <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              Select a workflow to view events
            </div>
          )}
          {selected && selectedWorkflow && (
            <div className="rounded-lg border bg-card p-4 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-foreground">{selectedWorkflow.workflow_type.replace(/_/g, ' ')}</p>
                <span className={`rounded border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[selectedWorkflow.workflow_status]}`}>
                  {selectedWorkflow.workflow_status}
                </span>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-2">Event history</p>
                {eventsLoading && [...Array(3)].map((_, i) => (
                  <div key={i} className="h-10 rounded bg-muted animate-pulse mb-2" />
                ))}
                {!eventsLoading && events.length === 0 && (
                  <p className="text-xs text-muted-foreground">No events</p>
                )}
                {!eventsLoading && events.map((ev, i) => (
                  <div key={ev.id} className="flex gap-3 pb-3">
                    <div className="flex flex-col items-center flex-shrink-0">
                      <div className="h-2 w-2 rounded-full bg-teal-400 mt-1" />
                      {i < events.length - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                    </div>
                    <div className="flex-1 pb-1">
                      <p className="text-xs font-medium text-foreground">{ev.event_type.replace(/_/g, ' ')}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{new Date(ev.created_at).toLocaleString()} · {ev.actor_type}</p>
                      {Object.keys(ev.payload).length > 0 && (
                        <pre className="mt-1.5 rounded bg-muted p-2 text-xs text-muted-foreground overflow-x-auto">
                          {JSON.stringify(ev.payload, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}