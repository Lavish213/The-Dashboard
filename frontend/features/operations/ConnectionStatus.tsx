'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'

interface Connections { status: string; checked_at: string; components: Array<{id: string; status: string}>; outbound_enabled: boolean | null; background_jobs_enabled: boolean | null }

const labels: Record<string, string> = {dashboard_database: 'Dashboard database', dashboard_to_sophia: 'Dashboard → Sophia', sophia_to_dashboard: 'Sophia → this dashboard', bob_shared_database_and_worker: 'Bob database and worker', sophia_dashboard_journal: 'Sophia delivery recovery'}

export function ConnectionStatus() {
  const query = useQuery({queryKey: ['project-connections'], queryFn: ({signal}) => apiFetch<Connections>('/api/v1/source-review/connections', {signal}), refetchInterval: 15000, retry: false})
  return <section aria-label="Project connections" className="mb-6 rounded-lg border bg-card p-4 space-y-3">
    <h2 className="font-semibold">Bob, Sophia and dashboard connections</h2>
    <p className="text-sm">Checks authenticated service connections and reported worker health. Calls, messages, calendar delivery and pricing accuracy need separate verification.</p>
    {query.isPending && <p role="status">Checking project connections…</p>}
    {query.isError && <p role="alert">Connection status unavailable. Previous results may be stale.</p>}
    {query.data && <><p className="text-sm font-medium">{query.isError ? 'Last reported status' : 'Connection status'}: {query.data.status}</p><dl className="grid gap-2 text-sm sm:grid-cols-2">{query.data.components.map(component => <div key={component.id}><dt>{labels[component.id] ?? component.id}</dt><dd>{component.status.replaceAll('_',' ')}</dd></div>)}</dl><p className="text-sm">Outbound: {query.data.outbound_enabled === null ? 'unknown' : query.data.outbound_enabled ? 'enabled' : 'disabled'} · Background jobs: {query.data.background_jobs_enabled === null ? 'unknown' : query.data.background_jobs_enabled ? 'enabled' : 'disabled'}</p><p className="text-xs text-muted-foreground">Checked <time dateTime={query.data.checked_at}>{new Date(query.data.checked_at).toLocaleString()}</time></p></>}
    <Button variant="outline" disabled={query.isFetching} onClick={() => void query.refetch()}>Recheck project connections</Button>
  </section>
}
