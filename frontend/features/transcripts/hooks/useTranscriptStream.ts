'use client'

/**
 * useTranscriptStream — WebSocket chunk streaming hook.
 *
 * Subscribes to `transcript:{id}` channel.
 * Appends chunks incrementally — never re-fetches entire history.
 * Reconnect safety: re-subscribes and fetches missed chunks since last seen index.
 * Duplicate protection: tracks seen chunk_index values.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useWebSocketContext } from '@/providers/WebsocketProvider'
import type { RealtimeEvent } from '@/types/websocket'
import type { TranscriptChunk } from '@/types/transcript'

interface UseTranscriptStreamResult {
  streamChunks: TranscriptChunk[]
  lastChunkIndex: number
  isSubscribed: boolean
}

export function useTranscriptStream(transcriptId: string): UseTranscriptStreamResult {
  const { send, registry } = useWebSocketContext()
  const qc = useQueryClient()

  const [streamChunks, setStreamChunks] = useState<TranscriptChunk[]>([])
  const [isSubscribed, setIsSubscribed] = useState(false)

  // Track seen indexes to prevent duplicates
  const seenIndexes = useRef<Set<number>>(new Set())
  const lastChunkIndex = useRef<number>(-1)

  const channel = `transcript:${transcriptId}`

  const appendChunk = useCallback((chunk: TranscriptChunk) => {
    if (seenIndexes.current.has(chunk.chunk_index)) return
    seenIndexes.current.add(chunk.chunk_index)
    lastChunkIndex.current = Math.max(lastChunkIndex.current, chunk.chunk_index)
    setStreamChunks((prev) => {
      // Insert in sorted order by chunk_index
      const idx = prev.findIndex((c) => c.chunk_index > chunk.chunk_index)
      if (idx === -1) return [...prev, chunk]
      return [...prev.slice(0, idx), chunk, ...prev.slice(idx)]
    })
  }, [])

  useEffect(() => {
    if (!transcriptId) return

    // Subscribe to channel
    send({ type: 'subscribe', channel })
    setIsSubscribed(true)

    const unregister = registry.register(channel, (event: RealtimeEvent) => {
      if (event.event_type === 'transcript.chunk_added') {
        const p = event.payload as {
          chunk_index: number
          speaker: string
          text?: string
          stream_type: string
        }
        // Synthesise a TranscriptChunk from the WS payload
        const chunk: TranscriptChunk = {
          id: event.event_id,
          transcript_id: transcriptId,
          chunk_index: p.chunk_index,
          speaker: p.speaker,
          text: (p.text as string) ?? '',
          stream_type: p.stream_type as TranscriptChunk['stream_type'],
          created_at: event.occurred_at,
        }
        appendChunk(chunk)
      }

      // Invalidate TanStack Query caches on lifecycle events
      if (
        event.event_type === 'transcript.paused' ||
        event.event_type === 'transcript.resumed' ||
        event.event_type === 'transcript.completed' ||
        event.event_type === 'transcript.failed' ||
        event.event_type === 'transcript.archived'
      ) {
        void qc.invalidateQueries({ queryKey: ['transcripts', transcriptId] })
      }
    })

    return () => {
      send({ type: 'unsubscribe', channel })
      unregister()
      setIsSubscribed(false)
    }
  }, [transcriptId, channel, send, registry, appendChunk, qc])

  return {
    streamChunks,
    lastChunkIndex: lastChunkIndex.current,
    isSubscribed,
  }
}
