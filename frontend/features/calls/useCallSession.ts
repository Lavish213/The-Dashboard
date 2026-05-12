'use client'

/**
 * useCallSession — queries, mutations, and realtime stream for a call session.
 *
 * Realtime: subscribes to `call:{sessionId}` channel.
 * On any call.* event: incremental state update — never full reload.
 * Reconnect-safe: re-subscribes on reconnect; TanStack Query refetches on invalidation.
 * Deduplication: server sequence numbers prevent double-processing.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useWebSocketContext } from '@/providers/WebsocketProvider'
import type { RealtimeEvent } from '@/types/websocket'
import type { CallEvent, JoinSessionBody } from '@/types/call'
import { callsApi } from './api'

const KEYS = {
  detail: (id: string) => ['calls', id] as const,
  participants: (id: string) => ['calls', id, 'participants'] as const,
  events: (id: string, page: number) => ['calls', id, 'events', page] as const,
  presence: (id: string) => ['calls', id, 'presence'] as const,
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useCallSession(sessionId: string) {
  return useQuery({
    queryKey: KEYS.detail(sessionId),
    queryFn: () => callsApi.get(sessionId),
    enabled: !!sessionId,
  })
}

export function useCallParticipants(sessionId: string) {
  return useQuery({
    queryKey: KEYS.participants(sessionId),
    queryFn: () => callsApi.participants(sessionId),
    enabled: !!sessionId,
  })
}

export function useCallEvents(sessionId: string, page = 1) {
  return useQuery({
    queryKey: KEYS.events(sessionId, page),
    queryFn: () => callsApi.events(sessionId, page),
    enabled: !!sessionId,
  })
}

export function useCallPresence(sessionId: string) {
  return useQuery({
    queryKey: KEYS.presence(sessionId),
    queryFn: () => callsApi.presence(sessionId),
    enabled: !!sessionId,
    refetchInterval: 15_000, // supplement realtime with periodic refresh
  })
}

// ── Mutations ────────────────────────────────────────────────────────────────

export function useCompleteSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: string) => callsApi.complete(sessionId),
    onSuccess: (_, sessionId) => {
      void qc.invalidateQueries({ queryKey: KEYS.detail(sessionId) })
    },
  })
}

export function useFailSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, reason }: { sessionId: string; reason?: string }) =>
      callsApi.fail(sessionId, reason),
    onSuccess: (_, { sessionId }) => {
      void qc.invalidateQueries({ queryKey: KEYS.detail(sessionId) })
    },
  })
}

export function useJoinSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, body }: { sessionId: string; body: JoinSessionBody }) =>
      callsApi.join(sessionId, body),
    onSuccess: (_, { sessionId }) => {
      void qc.invalidateQueries({ queryKey: KEYS.participants(sessionId) })
      void qc.invalidateQueries({ queryKey: KEYS.detail(sessionId) })
    },
  })
}

export function useLeaveSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, participantId }: { sessionId: string; participantId: string }) =>
      callsApi.leave(sessionId, participantId),
    onSuccess: (_, { sessionId }) => {
      void qc.invalidateQueries({ queryKey: KEYS.participants(sessionId) })
    },
  })
}

// ── Realtime stream ──────────────────────────────────────────────────────────

interface UseCallStreamResult {
  streamEvents: CallEvent[]
  lastSequence: number
  isSubscribed: boolean
}

export function useCallStream(sessionId: string): UseCallStreamResult {
  const { send, registry } = useWebSocketContext()
  const qc = useQueryClient()

  const [streamEvents, setStreamEvents] = useState<CallEvent[]>([])
  const [isSubscribed, setIsSubscribed] = useState(false)

  const seenSequences = useRef<Set<number>>(new Set())
  const lastSequence = useRef<number>(-1)

  const channel = `call:${sessionId}`

  const appendEvent = useCallback((event: CallEvent) => {
    if (seenSequences.current.has(event.sequence)) return
    seenSequences.current.add(event.sequence)
    lastSequence.current = Math.max(lastSequence.current, event.sequence)
    setStreamEvents((prev) => {
      // Insert in sequence order
      const idx = prev.findIndex((e) => e.sequence > event.sequence)
      if (idx === -1) return [...prev, event]
      return [...prev.slice(0, idx), event, ...prev.slice(idx)]
    })
  }, [])

  useEffect(() => {
    if (!sessionId) return

    send({ type: 'subscribe', channel })
    setIsSubscribed(true)

    const unregister = registry.register(channel, (wsEvent: RealtimeEvent) => {
      // Synthesise a CallEvent from WS payload
      const p = wsEvent.payload as {
        session_id?: string
        sequence?: number
        [key: string]: unknown
      }

      const callEvent: CallEvent = {
        id: wsEvent.event_id,
        session_id: (p.session_id as string) ?? sessionId,
        event_type: wsEvent.event_type,
        sequence: (p.sequence as number) ?? 0,
        payload: wsEvent.payload,
        created_at: wsEvent.occurred_at,
      }

      appendEvent(callEvent)

      // Invalidate derived queries on lifecycle events
      switch (wsEvent.event_type) {
        case 'call.session_started':
        case 'call.session_completed':
        case 'call.session_failed':
          void qc.invalidateQueries({ queryKey: KEYS.detail(sessionId) })
          break

        case 'call.participant_joined':
        case 'call.participant_left':
        case 'call.participant_reconnected':
        case 'call.participant_dropped':
          void qc.invalidateQueries({ queryKey: KEYS.participants(sessionId) })
          void qc.invalidateQueries({ queryKey: KEYS.presence(sessionId) })
          break
      }
    })

    return () => {
      send({ type: 'unsubscribe', channel })
      unregister()
      setIsSubscribed(false)
    }
  }, [sessionId, channel, send, registry, appendEvent, qc])

  return {
    streamEvents,
    lastSequence: lastSequence.current,
    isSubscribed,
  }
}
