import env from '@/config/environment'
import type {
  Approval,
  ApprovalCreateBody,
  ApprovalPage,
  ApprovalResolveBody,
  ApprovalType,
} from '@/types/approval'

const BASE = `${env.apiUrl}/api/v1/approvals`

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

export const approvalsApi = {
  request: (body: ApprovalCreateBody) =>
    request<Approval>('/request', { method: 'POST', body: JSON.stringify(body) }),

  resolve: (id: string, body: ApprovalResolveBody) =>
    request<Approval>(`/${id}/resolve`, { method: 'POST', body: JSON.stringify(body) }),

  get: (id: string) =>
    request<Approval>(`/${id}`),

  pending: (page = 1, pageSize = 20, approvalType?: ApprovalType) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (approvalType) params.set('approval_type', approvalType)
    return request<ApprovalPage>(`/pending?${params.toString()}`)
  },

  byWorkflow: (workflowId: string) =>
    request<Approval[]>(`/workflow/${workflowId}`),
}
