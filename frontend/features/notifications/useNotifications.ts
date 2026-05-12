'use client'

import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useWebSocketContext } from '@/providers/WebsocketProvider'
import type { RealtimeEvent } from '@/types/websocket'
import { notificationsApi } from './api'

const KEYS = {
  list: (userId: string, page: number, pageSize: number, unreadOnly: boolean) =>
    ['notifications', 'list', userId, page, pageSize, unreadOnly] as const,
  unreadCount: (userId: string) => ['notifications', 'unread-count', userId] as const,
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useNotifications(
  userId: string,
  page = 1,
  pageSize = 20,
  unreadOnly = false
) {
  return useQuery({
    queryKey: KEYS.list(userId, page, pageSize, unreadOnly),
    queryFn: () => notificationsApi.list(userId, page, pageSize, unreadOnly),
    enabled: !!userId,
  })
}

export function useUnreadCount(userId: string) {
  return useQuery({
    queryKey: KEYS.unreadCount(userId),
    queryFn: () => notificationsApi.unreadCount(userId),
    enabled: !!userId,
    refetchInterval: 30_000,
  })
}

// ── Mutations ────────────────────────────────────────────────────────────────

export function useMarkRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, userId }: { id: string; userId: string }) =>
      notificationsApi.markRead(id, userId),
    onSuccess: (_, { userId }) => {
      void qc.invalidateQueries({ queryKey: ['notifications', 'list', userId] })
      void qc.invalidateQueries({ queryKey: KEYS.unreadCount(userId) })
    },
  })
}

export function useMarkAllRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => notificationsApi.markAllRead(userId),
    onSuccess: (_, userId) => {
      void qc.invalidateQueries({ queryKey: ['notifications', 'list', userId] })
      void qc.invalidateQueries({ queryKey: KEYS.unreadCount(userId) })
    },
  })
}

// ── Realtime stream ──────────────────────────────────────────────────────────

export function useNotificationStream(userId: string) {
  const { send, registry } = useWebSocketContext()
  const qc = useQueryClient()

  const channel = `user:${userId}`

  useEffect(() => {
    if (!userId) return

    send({ type: 'subscribe', channel })

    const unregister = registry.register(channel, (event: RealtimeEvent) => {
      if (event.event_type === 'notification.created') {
        void qc.invalidateQueries({ queryKey: KEYS.unreadCount(userId) })
        void qc.invalidateQueries({ queryKey: ['notifications', 'list', userId] })
      }
    })

    return () => {
      send({ type: 'unsubscribe', channel })
      unregister()
    }
  }, [userId, channel, send, registry, qc])
}
