'use client'

import { useEffect, useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { apiFetch } from '@/services/api'

interface Transcript {
  id: string
  source_type: string
  transcript_status: string
  call_id: string | null
  lead_id: string | null
  workflow_id: string | null
  chunk_count: number
  created_at: string
}

interface Chunk {
  id: string
  speaker: string
  text: string
  chunk_index: number
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-muted text-muted-foreground border-border',
  active: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  paused: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  completed: 'bg-green-500/10 text-green-400 border-green-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  archived: 'bg-muted text-muted-foreground border-border',
}

export default function TranscriptsPage() {
  const [transcripts, setTranscripts] = useState<Transcript[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [chunks, setChunks] = useState<Chunk[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    apiFetch<{ items: Transcript[]; total: number }>('/api/v1/transcripts?page_size=100')
      .then((r) => { setTranscripts(r.items ?? []); setTotal(r.total ?? 0) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function loadChunks(id: string) {
    setSelected(id)
    setChunksLoading(true)
    try {
      const result = await apiFetch<Chunk[]>(`/api/v1/transcripts/${id}/chunks?page_size=200`)
      setChunks(Array.isArray(result) ? result : [])
    } catch {
      setChunks([])
    } finally {
      setChunksLoading(false)
    }
  }

  return (
    <PageContainer title="Transcripts" description={`${total} transcripts`}>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground px-1">
            {transcripts.length} transcripts
          </p>
          {loading && [...Array(3)].map((_, i) => (
            <div key={i} className="h-16 rounded-lg border bg-card animate-pulse" />
          ))}
          {!loading && transcripts.length === 0 && (
            <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              No transcripts yet
            </div>
          )}
          {!loading && transcripts.map((t) => (
            <button
              key={t.id}
              onClick={() => loadChunks(t.id)}
              className={`w-full text-left rounded-lg border p-3 transition-colors hover:bg-muted/30 ${selected === t.id ? 'border-teal-500/30 bg-teal-500/5' : 'bg-card'}`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {t.source_type} transcript
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                    {t.id.slice(0, 8)}…
                  </p>
                </div>
                <span className={`flex-shrink-0 rounded border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[t.transcript_status] ?? 'bg-muted text-muted-foreground border-border'}`}>
                  {t.transcript_status}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1.5">
                {new Date(t.created_at).toLocaleString()}
              </p>
            </button>
          ))}
        </div>

        <div>
          {!selected && (
            <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              Select a transcript to view chunks
            </div>
          )}
          {selected && (
            <div className="rounded-lg border bg-card p-4 space-y-3 max-h-[600px] overflow-y-auto">
              <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                Transcript
              </p>
              {chunksLoading && [...Array(4)].map((_, i) => (
                <div key={i} className="h-12 rounded bg-muted animate-pulse" />
              ))}
              {!chunksLoading && chunks.length === 0 && (
                <p className="text-xs text-muted-foreground">No chunks yet</p>
              )}
              {!chunksLoading && chunks.map((chunk) => (
                <div key={chunk.id} className="flex gap-3">
                  <div className="w-14 flex-shrink-0">
                    <span className={`text-xs font-semibold ${chunk.speaker === 'sophia' ? 'text-teal-400' : 'text-muted-foreground'}`}>
                      {chunk.speaker}
                    </span>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed flex-1">
                    {chunk.text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}