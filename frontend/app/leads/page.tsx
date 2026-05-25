'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQueryState, parseAsString } from 'nuqs'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { PageContainer } from '@/components/workspace/PageContainer'
import { SkeletonKanban } from '@/components/ui/skeleton-states'
import { LeadAvatar } from '@/components/leads/LeadAvatar'
import { apiFetch } from '@/services/api'
import { toast } from 'sonner'
import { scoreColor } from '@/constants/colors'

type LeadStatus = 'new' | 'contacted' | 'qualified' | 'disqualified' | 'converted' | 'dead'

interface Lead {
  id: string
  full_name: string
  phone: string | null
  email: string | null
  lead_status: LeadStatus
  lead_source: string | null
  ai_score: number | null
  last_contacted_at: string | null
  created_at: string
}

const STAGES: { key: LeadStatus; label: string }[] = [
  { key: 'new', label: 'New' },
  { key: 'contacted', label: 'Contacted' },
  { key: 'qualified', label: 'Qualified' },
  { key: 'disqualified', label: 'Disqualified' },
  { key: 'converted', label: 'Converted' },
  { key: 'dead', label: 'Dead' },
]

function LeadCard({ lead, isDragging }: { lead: Lead; isDragging?: boolean }) {
  const sc = scoreColor(lead.ai_score)
  const isHighScore = lead.ai_score != null && lead.ai_score >= 8

  return (
    <div
      className={`rounded-lg border p-3 space-y-2 transition-all ${
        isDragging
          ? 'opacity-50 shadow-elevated rotate-1 scale-105'
          : isHighScore
          ? 'border-amber-500/20 bg-amber-500/5 hover:border-amber-500/30'
          : 'border-border bg-card hover:border-border/80 hover:shadow-card'
      }`}
    >
      <div className="flex items-start gap-2">
        <LeadAvatar name={lead.full_name} score={lead.ai_score} size="sm" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground leading-tight truncate">
            {lead.full_name}
          </p>
          {lead.phone && (
            <p className="text-xs text-muted-foreground mt-0.5 font-mono">{lead.phone}</p>
          )}
        </div>
        {lead.ai_score != null && (
          <span className={`text-xs font-semibold tabular-nums flex-shrink-0 ${sc.text}`}>
            {lead.ai_score}
          </span>
        )}
      </div>
      {lead.lead_source && (
        <div className="flex items-center gap-1.5">
          <span className="rounded border border-border bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
            {lead.lead_source}
          </span>
        </div>
      )}
    </div>
  )
}

function SortableLeadCard({ lead }: { lead: Lead }) {
  const router = useRouter()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: lead.id,
    data: { lead },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    cursor: isDragging ? 'grabbing' : 'grab',
  }

  function handleClick() {
    if (isDragging) return
    router.push(`/leads/${lead.id}`)
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} onClick={handleClick}>
      <LeadCard lead={lead} isDragging={isDragging} />
    </div>
  )
}

function KanbanColumn({ stage, leads }: { stage: { key: LeadStatus; label: string }; leads: Lead[] }) {
  return (
    <div className="min-w-[240px] flex-shrink-0">
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          {stage.label}
        </span>
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground tabular-nums">
          {leads.length}
        </span>
      </div>
      <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-2 min-h-[60px] rounded-lg p-1 transition-colors" data-stage={stage.key}>
          {leads.length === 0 && (
            <div className="rounded-lg border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
              Drop here
            </div>
          )}
          {leads.map((lead) => (
            <SortableLeadCard key={lead.id} lead={lead} />
          ))}
        </div>
      </SortableContext>
    </div>
  )
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [stageFilter] = useQueryState('stage', parseAsString.withDefault(''))

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ page_size: '200' })
    if (stageFilter) params.set('status', stageFilter)
    apiFetch<{ items: Lead[] }>(`/api/v1/leads?${params}`)
      .then((r) => setLeads(r.items))
      .catch((e: Error) => toast.error('Failed to load leads', { description: e.message }))
      .finally(() => setLoading(false))
  }, [stageFilter])

  const activeLead = activeId ? leads.find((l) => l.id === activeId) : null

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as string)
  }

  async function handleDragEnd(event: DragEndEvent) {
    setActiveId(null)
    const { active, over } = event
    if (!over) return

    const draggedLead = leads.find((l) => l.id === active.id)
    if (!draggedLead) return

    let targetStage: LeadStatus | null = null
    const overLead = leads.find((l) => l.id === over.id)
    if (overLead) {
      targetStage = overLead.lead_status
    } else {
      const stageKey = over.id as string
      if (STAGES.some((s) => s.key === stageKey)) {
        targetStage = stageKey as LeadStatus
      }
    }

    if (!targetStage || targetStage === draggedLead.lead_status) return

    setLeads((prev) =>
      prev.map((l) => (l.id === draggedLead.id ? { ...l, lead_status: targetStage! } : l))
    )

    try {
      await apiFetch(`/api/v1/leads/${draggedLead.id}/status?status=${targetStage}`, { method: 'PATCH' })
      toast.success(`${draggedLead.full_name} moved to ${targetStage}`)
    } catch {
      setLeads((prev) =>
        prev.map((l) =>
          l.id === draggedLead.id ? { ...l, lead_status: draggedLead.lead_status } : l
        )
      )
      toast.error('Failed to move lead')
    }
  }

  const byStage = (status: LeadStatus) => leads.filter((l) => l.lead_status === status)

  return (
    <PageContainer title="Lead Pipeline" description={`${leads.length} total leads`}>
      {loading ? (
        <SkeletonKanban />
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-3 overflow-x-auto pb-4">
            {STAGES.map((stage) => (
              <KanbanColumn key={stage.key} stage={stage} leads={byStage(stage.key)} />
            ))}
          </div>
          <DragOverlay>
            {activeLead ? (
              <div className="opacity-95 rotate-1 shadow-modal">
                <LeadCard lead={activeLead} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}
    </PageContainer>
  )
}