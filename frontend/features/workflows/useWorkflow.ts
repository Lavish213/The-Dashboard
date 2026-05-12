'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { workflowsApi } from './api'

const KEYS = {
  detail: (id: string) => ['workflows', id] as const,
  events: (id: string) => ['workflows', id, 'events'] as const,
  replay: (id: string) => ['workflows', id, 'replay'] as const,
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => workflowsApi.get(id),
    enabled: !!id,
  })
}

export function useWorkflowEvents(id: string) {
  return useQuery({
    queryKey: KEYS.events(id),
    queryFn: () => workflowsApi.events(id),
    enabled: !!id,
  })
}

export function useWorkflowReplay(id: string) {
  return useQuery({
    queryKey: KEYS.replay(id),
    queryFn: () => workflowsApi.replay(id),
    enabled: !!id,
  })
}

// Mutation factory — invalidates workflow detail on success
function useWorkflowMutation(action: (id: string) => Promise<unknown>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: action,
    onSuccess: (_data, id) => {
      void qc.invalidateQueries({ queryKey: KEYS.detail(id) })
      void qc.invalidateQueries({ queryKey: KEYS.events(id) })
    },
  })
}

export function usePauseWorkflow() {
  return useWorkflowMutation(workflowsApi.pause)
}

export function useResumeWorkflow() {
  return useWorkflowMutation(workflowsApi.resume)
}

export function useCancelWorkflow() {
  return useWorkflowMutation(workflowsApi.cancel)
}

export function useRecoverWorkflow() {
  return useWorkflowMutation(workflowsApi.recover)
}
