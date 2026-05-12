'use client'

import { useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { TranscriptChunk } from '@/types/transcript'
import {
  useTranscriptQuery,
  useTranscriptChunks,
  usePauseTranscript,
  useResumeTranscript,
  useCompleteTranscript,
  useArchiveTranscript,
} from '../hooks/useTranscript'
import { useTranscriptStream } from '../hooks/useTranscriptStream'
import { TranscriptStatusBadge } from './TranscriptStatusBadge'

interface Props {
  transcriptId: string
}

// Max chunks to render at once — prevents unbounded DOM growth
const MAX_RENDERED_CHUNKS = 200

function ChunkRow({ chunk }: { chunk: TranscriptChunk }) {
  const isAgent = chunk.stream_type === 'agent'
  return (
    <div className={`flex gap-3 py-2 ${isAgent ? 'flex-row' : 'flex-row-reverse'}`}>
      <span className="shrink-0 text-xs font-medium text-muted-foreground w-14 pt-0.5 text-right">
        {chunk.speaker}
      </span>
      <div
        className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
          isAgent
            ? 'bg-muted text-foreground'
            : 'bg-primary text-primary-foreground'
        }`}
      >
        {chunk.text}
      </div>
    </div>
  )
}

export function TranscriptViewer({ transcriptId }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [historyPage, setHistoryPage] = useState(1)

  const { data: transcript, isLoading, error } = useTranscriptQuery(transcriptId)
  const { data: historicalChunks = [] } = useTranscriptChunks(transcriptId, historyPage)
  const { streamChunks, isSubscribed } = useTranscriptStream(transcriptId)

  const pause = usePauseTranscript()
  const resume = useResumeTranscript()
  const complete = useCompleteTranscript()
  const archive = useArchiveTranscript()

  // Merge historical + stream, deduplicate by chunk_index, sort, trim to MAX
  const allChunks = (() => {
    const seenIdx = new Set<number>()
    const merged: TranscriptChunk[] = []
    for (const c of [...historicalChunks, ...streamChunks]) {
      if (!seenIdx.has(c.chunk_index)) {
        seenIdx.add(c.chunk_index)
        merged.push(c)
      }
    }
    merged.sort((a, b) => a.chunk_index - b.chunk_index)
    // Keep last MAX_RENDERED_CHUNKS to avoid unbounded DOM growth
    return merged.slice(-MAX_RENDERED_CHUNKS)
  })()

  // Auto-scroll to bottom on new chunks
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [allChunks.length])

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    )
  }

  if (error || !transcript) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-destructive">
        Transcript not found.
      </div>
    )
  }

  const status = transcript.transcript_status

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-base truncate">
            Transcript
            {transcript.duration_seconds != null && (
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {Math.floor(transcript.duration_seconds / 60)}m{' '}
                {transcript.duration_seconds % 60}s
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-2 shrink-0">
            <TranscriptStatusBadge status={status} />
            {isSubscribed && status === 'active' && (
              <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" title="Live" />
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 flex-wrap pt-1">
          {status === 'active' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => pause.mutate(transcriptId)}
              disabled={pause.isPending}
            >
              Pause
            </Button>
          )}
          {status === 'paused' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => resume.mutate(transcriptId)}
              disabled={resume.isPending}
            >
              Resume
            </Button>
          )}
          {(status === 'active' || status === 'paused') && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => complete.mutate(transcriptId)}
              disabled={complete.isPending}
            >
              Complete
            </Button>
          )}
          {(status === 'completed' || status === 'failed') && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => archive.mutate(transcriptId)}
              disabled={archive.isPending}
            >
              Archive
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto min-h-0 px-4">
        {allChunks.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            {status === 'created' ? 'Transcript not yet started.' : 'No chunks yet.'}
          </div>
        ) : (
          <div className="divide-y divide-border/30">
            {allChunks.length >= MAX_RENDERED_CHUNKS && (
              <button
                onClick={() => setHistoryPage((p) => p + 1)}
                className="w-full py-2 text-xs text-muted-foreground hover:text-foreground"
              >
                Load earlier…
              </button>
            )}
            {allChunks.map((chunk) => (
              <ChunkRow key={chunk.id} chunk={chunk} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </CardContent>
    </Card>
  )
}
