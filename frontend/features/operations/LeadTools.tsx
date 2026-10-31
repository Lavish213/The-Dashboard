'use client'

import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth.store'

interface ImportResult { parsed: number; upserted: number; scored: number; leads_created: number; skipped_score: number; errors: number }

const MAX_BYTES = 10 * 1024 * 1024

export function LeadTools() {
  const user = useAuthStore(state => state.user)
  const client = useQueryClient()
  const [busy, setBusy] = useState<'' | 'download' | 'import'>('')
  const [message, setMessage] = useState('')
  const [file, setFile] = useState<File | null>(null)
  if (user?.role !== 'admin') return null

  async function download(pricedOnly: boolean) {
    setBusy('download')
    setMessage('')
    try {
      const csv = await apiFetch<string>(`/api/v1/source-review/mail-list.csv?priced_only=${pricedOnly}`, {}, { timeoutMs: 60_000, text: true })
      const rows = Math.max(0, csv.trim().split('\n').length - 1)
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
      const link = document.createElement('a')
      link.href = url
      link.download = pricedOnly ? 'mail-list-priced.csv' : 'mail-list-all.csv'
      link.click()
      URL.revokeObjectURL(url)
      setMessage(`Downloaded ${rows} mailing rows.`)
    } catch {
      setMessage('Mail list could not be downloaded.')
    } finally {
      setBusy('')
    }
  }

  async function upload() {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.csv') || file.size === 0 || file.size > MAX_BYTES) {
      setMessage('Choose a CSV file under 10MB.')
      return
    }
    setBusy('import')
    setMessage('')
    try {
      const result = await apiFetch<ImportResult>('/api/v1/source-review/import-csv', { method: 'POST', body: file, headers: { 'Content-Type': 'text/csv' } }, { timeoutMs: 900_000 })
      setMessage(`Imported ${result.upserted} of ${result.parsed} rows. New leads ${result.leads_created}. Errors ${result.errors}.`)
      setFile(null)
      void client.invalidateQueries({ queryKey: ['data-quality'] })
      void client.invalidateQueries({ queryKey: ['rentcast-usage'] })
    } catch {
      setMessage('Import could not be confirmed. Check data quality before uploading again.')
    } finally {
      setBusy('')
    }
  }

  return <section className="mb-6 rounded-lg border bg-card p-4 space-y-3" aria-label="Lead tools">
    <h2 className="font-semibold">Lead tools</h2>
    <div className="flex flex-wrap gap-2">
      <Button disabled={busy !== ''} onClick={() => void download(true)}>Download priced mail list</Button>
      <Button variant="outline" disabled={busy !== ''} onClick={() => void download(false)}>Download full mail list</Button>
    </div>
    <p className="text-xs text-muted-foreground">Leads with a mailing address. Opted out owners and denied ownership are left out. Values come from RentCast listing comps.</p>
    <div className="flex flex-wrap items-end gap-2">
      <label className="text-sm">Propwire CSV<input type="file" accept=".csv,text/csv" onChange={event => setFile(event.target.files?.[0] ?? null)} className="block text-sm" /></label>
      <Button variant="outline" disabled={busy !== '' || !file} onClick={() => void upload()}>{busy === 'import' ? 'Importing…' : 'Import leads'}</Button>
    </div>
    <p className="text-xs text-muted-foreground">Import scores each house and creates leads. The import itself never calls, texts or emails anyone.</p>
    {message && <p role="status" className="text-sm">{message}</p>}
  </section>
}
