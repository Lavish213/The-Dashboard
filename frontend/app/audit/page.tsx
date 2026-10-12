'use client'

import { useQuery } from '@tanstack/react-query'
import { useQueryState, parseAsInteger } from 'nuqs'
import { PageContainer } from '@/components/workspace/PageContainer'
import { SkeletonTable } from '@/components/ui/skeleton-states'
import { apiFetch } from '@/services/api'

interface AuditLog {
  id: string
  actor_type: string
  actor_id: string | null
  action: string
  target_type: string
  target_id: string | null
  created_at: string
}

export default function AuditPage() {
  const [page, setPage] = useQueryState('page', parseAsInteger.withDefault(1))

  const { data, isPending: loading, error } = useQuery({
    queryKey: ['audit', page],
    queryFn: ({ signal }) => apiFetch<{ items: AuditLog[]; total: number; total_pages: number }>(`/api/v1/audit?page=${page}&page_size=50`, { signal }),
  })
  const logs = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  return (
    <PageContainer title="Audit Log" description={`${total} total events — immutable record`}>
      {error && <p role="alert" className="text-sm text-destructive">Audit records could not be loaded.</p>}
      {loading ? (
        <SkeletonTable rows={10} cols={4} />
      ) : (
        <div className="rounded-lg border bg-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Time</th>
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Actor</th>
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Action</th>
                <th className="text-left px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">Target</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-12 text-center text-sm text-muted-foreground">No audit events yet</td></tr>
              )}
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 text-xs font-mono text-muted-foreground whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-foreground">{log.actor_type}</span>
                    {log.actor_id && <span className="text-xs text-muted-foreground font-mono ml-1">{log.actor_id.slice(0, 6)}…</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded border border-border bg-muted px-2 py-0.5 text-xs text-foreground font-mono">{log.action}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {log.target_type}
                    {log.target_id && <span className="font-mono ml-1">{log.target_id.slice(0, 6)}…</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-4">
          <button disabled={page === 1} onClick={() => setPage(page - 1)} className="rounded border px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-muted transition-colors">Previous</button>
          <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
          <button disabled={page === totalPages} onClick={() => setPage(page + 1)} className="rounded border px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-muted transition-colors">Next</button>
        </div>
      )}
    </PageContainer>
  )
}
