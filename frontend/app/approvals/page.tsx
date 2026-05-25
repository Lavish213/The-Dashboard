'use client'

import { useEffect, useState, useCallback } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { apiFetch, ApiError } from '@/services/api'
import { CheckCircle, XCircle, Clock, AlertTriangle, RefreshCw } from 'lucide-react'

type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired'
type RiskLevel = 'low' | 'medium' | 'high' | 'critical'
type ApprovalType = string

interface Approval {
  id: string
  workflow_id: string
  approval_type: ApprovalType
  approval_status: ApprovalStatus
  requested_by: string | null
  resolved_by: string | null
  expires_at: string | null
  risk_level: RiskLevel
  resolution_notes: string | null
  created_at: string
  updated_at: string
}

interface PendingResponse {
  items: Approval[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

const RISK_COLORS: Record<RiskLevel, string> = {
  low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
}

const STATUS_COLORS: Record<ApprovalStatus, string> = {
  pending: 'text-amber-400',
  approved: 'text-emerald-400',
  rejected: 'text-red-400',
  expired: 'text-muted-foreground',
}

function StatusIcon({ status }: { status: ApprovalStatus }) {
  if (status === 'approved') return <CheckCircle className="h-4 w-4 text-emerald-400" />
  if (status === 'rejected') return <XCircle className="h-4 w-4 text-red-400" />
  if (status === 'expired') return <AlertTriangle className="h-4 w-4 text-muted-foreground" />
  return <Clock className="h-4 w-4 text-amber-400" />
}

function ApprovalCard({
  approval,
  onResolve,
  resolving,
}: {
  approval: Approval
  onResolve: (id: string, approved: boolean) => void
  resolving: string | null
}) {
  const isPending = approval.approval_status === 'pending'
  const isResolving = resolving === approval.id
  const expiresAt = approval.expires_at ? new Date(approval.expires_at) : null
  const isExpiringSoon = expiresAt && expiresAt.getTime() - Date.now() < 1000 * 60 * 30

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <StatusIcon status={approval.approval_status} />
          <span className="font-mono text-xs text-muted-foreground truncate">
            {approval.approval_type.replace(/_/g, ' ')}
          </span>
        </div>
        <span
          className={`shrink-0 rounded border px-2 py-0.5 text-xs font-medium ${RISK_COLORS[approval.risk_level]}`}
        >
          {approval.risk_level}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <p className="text-muted-foreground">Workflow</p>
          <p className="font-mono truncate">{approval.workflow_id.slice(0, 8)}…</p>
        </div>
        <div>
          <p className="text-muted-foreground">Requested</p>
          <p>{new Date(approval.created_at).toLocaleString()}</p>
        </div>
        {expiresAt && (
          <div className="col-span-2">
            <p className={`text-muted-foreground ${isExpiringSoon ? 'text-amber-400' : ''}`}>
              {isExpiringSoon ? '⚠ Expires soon' : 'Expires'}
            </p>
            <p className={isExpiringSoon ? 'text-amber-400 font-medium' : ''}>
              {expiresAt.toLocaleString()}
            </p>
          </div>
        )}
        {approval.resolution_notes && (
          <div className="col-span-2">
            <p className="text-muted-foreground">Notes</p>
            <p className="italic">{approval.resolution_notes}</p>
          </div>
        )}
      </div>

      {isPending && (
        <div className="flex gap-2 pt-1">
          <button
            disabled={isResolving}
            onClick={() => onResolve(approval.id, true)}
            className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-50 transition-colors"
          >
            <CheckCircle className="h-3.5 w-3.5" />
            {isResolving ? 'Approving…' : 'Approve'}
          </button>
          <button
            disabled={isResolving}
            onClick={() => onResolve(approval.id, false)}
            className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-red-500/10 border border-red-500/20 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20 disabled:opacity-50 transition-colors"
          >
            <XCircle className="h-3.5 w-3.5" />
            {isResolving ? 'Rejecting…' : 'Reject'}
          </button>
        </div>
      )}
    </div>
  )
}

export default function ApprovalsPage() {
  const [data, setData] = useState<PendingResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [resolving, setResolving] = useState<string | null>(null)
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await apiFetch<PendingResponse>(
        `/api/v1/approvals/pending?page=${page}&page_size=20`,
      )
      setData(res)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to load approvals')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    load()
  }, [load])

  const handleResolve = async (approvalId: string, approved: boolean) => {
    setResolving(approvalId)
    try {
      await apiFetch(`/api/v1/approvals/${approvalId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({
          approval_status: approved ? 'approved' : 'rejected',
          resolved_by: null,
        }),
      })
      await load()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to resolve approval')
    } finally {
      setResolving(null)
    }
  }

  const pending = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  return (
    <PageContainer
      title="Approvals"
      description="Governance approval queue"
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {loading ? 'Loading…' : `${total} pending`}
            </span>
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}

        {!loading && pending.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center py-16 gap-2">
            <CheckCircle className="h-8 w-8 text-emerald-400" />
            <p className="text-sm text-muted-foreground">No pending approvals</p>
          </div>
        )}

        {loading && pending.length === 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="rounded-lg border bg-card p-4 h-36 animate-pulse" />
            ))}
          </div>
        )}

        {pending.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {pending.map((approval) => (
              <ApprovalCard
                key={approval.id}
                approval={approval}
                onResolve={handleResolve}
                resolving={resolving}
              />
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-2">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-md border px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-muted transition-colors"
            >
              Previous
            </button>
            <span className="text-xs text-muted-foreground">
              {page} / {totalPages}
            </span>
            <button
              disabled={page === totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-md border px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-muted transition-colors"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </PageContainer>
  )
}