import env from '@/config/environment'
import type { Workflow, WorkflowEvent, WorkflowReplay } from '@/types/workflow'

const BASE = `${env.apiUrl}/api/v1/workflows`

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

export const workflowsApi = {
  get: (id: string) => request<Workflow>(`/${id}`),

  pause: (id: string) =>
    request<Workflow>(`/${id}/pause`, { method: 'POST' }),

  resume: (id: string) =>
    request<Workflow>(`/${id}/resume`, { method: 'POST' }),

  cancel: (id: string) =>
    request<Workflow>(`/${id}/cancel`, { method: 'POST' }),

  complete: (id: string) =>
    request<Workflow>(`/${id}/complete`, { method: 'POST' }),

  recover: (id: string) =>
    request<Workflow>(`/${id}/recover`, { method: 'POST' }),

  events: (id: string) =>
    request<WorkflowEvent[]>(`/${id}/events`),

  replay: (id: string) =>
    request<WorkflowReplay>(`/${id}/replay`),
}
