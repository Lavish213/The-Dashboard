'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { operatorSessionsApi } from './api'

const KEYS = {
  list: (page: number, pageSize: number) =>
    ['operator-sessions', 'list', page, pageSize] as const,
  count: () => ['operator-sessions', 'count'] as const,
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useActiveSessions(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: KEYS.list(page, pageSize),
    queryFn: () => operatorSessionsApi.list(page, pageSize),
    refetchInterval: 30_000,
  })
}

export function useActiveSessionCount() {
  return useQuery({
    queryKey: KEYS.count(),
    queryFn: () => operatorSessionsApi.count(),
    refetchInterval: 15_000,
  })
}

// ── Mutations ────────────────────────────────────────────────────────────────

export function useDisconnectSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: string) => operatorSessionsApi.disconnect(sessionId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['operator-sessions'] })
    },
  })
}

export function useCleanupStale() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (thresholdSeconds?: number) =>
      operatorSessionsApi.cleanupStale(thresholdSeconds),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['operator-sessions'] })
    },
  })
}
