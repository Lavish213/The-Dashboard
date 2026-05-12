'use client'

/**
 * useApprovals — hooks for approval queries, mutations, and realtime updates.
 *
 * Realtime: subscribes to `approvals` channel.
 * On approval.requested / approval.resolved / approval.expired / approval.escalated:
 *   invalidates pending list and relevant detail queries.
 * Reconnect-safe: re-subscribes on reconnect; TanStack Query refetches on invalidation.
 * Duplicate safety: server sends idempotent events; invalidation is idempotent.
 */

import { useCallback, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useWebSocketContext } from '@/providers/WebsocketProvider'
import type { RealtimeEvent } from '@/types/websocket'
import type { ApprovalCreateBody, ApprovalResolveBody, ApprovalType } from '@/types/approval'
import { approvalsApi } from './api'

const APPROVAL_CHANNEL = 'approvals'

const KEYS = {
  pending: (page: number, pageSize: number, type?: ApprovalType) =>
    ['approvals', 'pending', page, pageSize, type ?? null] as const,
  detail: (id: string) => ['approvals', id] as const,
  byWorkflow: (workflowId: string) => ['approvals', 'workflow', workflowId] as const,
}

// ── Realtime subscription ───────────────────────────────────────────────────

export function useApprovalStream() {
  const { send, registry } = useWebSocketContext()
  const qc = useQueryClient()

  const invalidatePending = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ['approvals', 'pending'] })
  }, [qc])

  useEffect(() => {
    send({ type: 'subscribe', channel: APPROVAL_CHANNEL })

    const unregister = registry.register(APPROVAL_CHANNEL, (event: RealtimeEvent) => {
      const approvalId = event.payload.approval_id as string | undefined
      const workflowId = event.payload.workflow_id as string | undefined

      switch (event.event_type) {
        case 'approval.requested':
          invalidatePending()
          if (workflowId) {
            void qc.invalidateQueries({ queryKey: KEYS.byWorkflow(workflowId) })
          }
          break

        case 'approval.resolved':
        case 'approval.expired':
        case 'approval.escalated':
          invalidatePending()
          if (approvalId) {
            void qc.invalidateQueries({ queryKey: KEYS.detail(approvalId) })
          }
          if (workflowId) {
            void qc.invalidateQueries({ queryKey: KEYS.byWorkflow(workflowId) })
          }
          break
      }
    })

    return () => {
      send({ type: 'unsubscribe', channel: APPROVAL_CHANNEL })
      unregister()
    }
  }, [send, registry, qc, invalidatePending])
}

// ── Queries ─────────────────────────────────────────────────────────────────

export function usePendingApprovals(page = 1, pageSize = 20, type?: ApprovalType) {
  return useQuery({
    queryKey: KEYS.pending(page, pageSize, type),
    queryFn: () => approvalsApi.pending(page, pageSize, type),
  })
}

export function useApproval(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => approvalsApi.get(id),
    enabled: !!id,
  })
}

export function useWorkflowApprovals(workflowId: string) {
  return useQuery({
    queryKey: KEYS.byWorkflow(workflowId),
    queryFn: () => approvalsApi.byWorkflow(workflowId),
    enabled: !!workflowId,
  })
}

// ── Mutations ────────────────────────────────────────────────────────────────

export function useRequestApproval() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ApprovalCreateBody) => approvalsApi.request(body),
    onSuccess: (approval) => {
      void qc.invalidateQueries({ queryKey: ['approvals', 'pending'] })
      void qc.invalidateQueries({ queryKey: KEYS.byWorkflow(approval.workflow_id) })
    },
  })
}

export function useResolveApproval() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ApprovalResolveBody }) =>
      approvalsApi.resolve(id, body),
    onSuccess: (approval) => {
      void qc.invalidateQueries({ queryKey: ['approvals', 'pending'] })
      void qc.invalidateQueries({ queryKey: KEYS.detail(approval.id) })
      void qc.invalidateQueries({ queryKey: KEYS.byWorkflow(approval.workflow_id) })
    },
  })
}
