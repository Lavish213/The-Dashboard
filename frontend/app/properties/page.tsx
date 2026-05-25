'use client'

import { useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { Search, Home, User, DollarSign, Calendar, Landmark, ArrowRight } from 'lucide-react'
import { apiFetch } from '@/services/api'

interface PropertyResult {
  attomId: string
  address: string
  city: string
  state: string
  zip: string
  bedrooms: number | null
  bathrooms: number | null
  squareFeet: number | null
  yearBuilt: number | null
  estimatedValue: number | null
  lastSalePrice: number | null
  lastSaleDate: string | null
  ownerName: string | null
  lotSize: number | null
  propertyType: string | null
  taxAssessment: number | null
  taxDelinquent: boolean
}

function fmt$( v: number | null): string {
  if (!v) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v)
}

function fmtNum(v: number | null): string {
  if (!v) return '—'
  return new Intl.NumberFormat('en-US').format(v)
}

function equity(prop: PropertyResult): number | null {
  if (!prop.estimatedValue || !prop.lastSalePrice) return null
  return prop.estimatedValue - prop.lastSalePrice
}

function equityPct(prop: PropertyResult): string {
  const eq = equity(prop)
  if (!eq || !prop.estimatedValue) return '—'
  return `${Math.round((eq / prop.estimatedValue) * 100)}%`
}

export default function PropertiesPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<PropertyResult[]>([])
  const [selected, setSelected] = useState<PropertyResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [creatingLead, setCreatingLead] = useState(false)
  const [leadCreated, setLeadCreated] = useState(false)

  async function search() {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResults([])
    setSelected(null)
    setLeadCreated(false)
    try {
      const data = await apiFetch<PropertyResult[]>(
        `/api/v1/property-search?address=${encodeURIComponent(query)}`
      )
      setResults(data ?? [])
      if (data?.length === 1) setSelected(data[0])
    } catch (e: any) {
      setError(e.message ?? 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  async function createLead(prop: PropertyResult) {
    setCreatingLead(true)
    try {
      await apiFetch('/api/v1/leads', {
        method: 'POST',
        body: JSON.stringify({
          full_name: prop.ownerName ?? 'Unknown Owner',
          phone: null,
          lead_source: 'direct',
          lead_status: 'new',
          ai_score: prop.taxDelinquent ? 9 : 6,
        }),
      })
      setLeadCreated(true)
    } catch {
    } finally {
      setCreatingLead(false)
    }
  }

  return (
    <PageContainer title="Properties" description="Search and analyze properties for acquisition">
      <div className="space-y-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
              placeholder="Enter address or APN — e.g. 1234 Main St, Stockton CA"
              className="w-full rounded-lg border border-border bg-card pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-teal-500/50"
            />
          </div>
          <button
            onClick={search}
            disabled={loading || !query.trim()}
            className="rounded-lg border border-teal-500/25 bg-teal-500/10 px-4 py-2.5 text-sm font-medium text-teal-400 hover:bg-teal-500/20 transition-colors disabled:opacity-40"
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {!loading && results.length === 0 && !error && (
          <div className="rounded-lg border border-dashed border-border p-12 text-center">
            <Home className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-40" />
            <p className="text-sm text-muted-foreground">Search an address to pull property data</p>
            <p className="text-xs text-muted-foreground mt-1 opacity-60">Powered by ATTOM Data — owner info, AVM, tax records</p>
          </div>
        )}

        {results.length > 1 && (
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">{results.length} results</p>
            {results.map((r) => (
              <button
                key={r.attomId}
                onClick={() => setSelected(r)}
                className={`w-full text-left rounded-lg border p-3 transition-colors hover:bg-muted/30 ${selected?.attomId === r.attomId ? 'border-teal-500/30 bg-teal-500/5' : 'border-border bg-card'}`}
              >
                <p className="text-sm font-medium text-foreground">{r.address}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{r.city}, {r.state} {r.zip} · {r.propertyType ?? 'Residential'}</p>
              </button>
            ))}
          </div>
        )}

        {selected && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-4">
              <div className="rounded-lg border bg-card p-5">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <h2 className="text-base font-semibold text-foreground">{selected.address}</h2>
                    <p className="text-sm text-muted-foreground mt-0.5">{selected.city}, {selected.state} {selected.zip}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {selected.taxDelinquent && (
                      <span className="rounded border border-red-500/20 bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-400">
                        Tax Delinquent
                      </span>
                    )}
                    <span className="rounded border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      {selected.propertyType ?? 'Residential'}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-lg bg-muted p-3 text-center">
                    <p className="text-xs text-muted-foreground">Beds</p>
                    <p className="text-lg font-semibold text-foreground mt-0.5">{selected.bedrooms ?? '—'}</p>
                  </div>
                  <div className="rounded-lg bg-muted p-3 text-center">
                    <p className="text-xs text-muted-foreground">Baths</p>
                    <p className="text-lg font-semibold text-foreground mt-0.5">{selected.bathrooms ?? '—'}</p>
                  </div>
                  <div className="rounded-lg bg-muted p-3 text-center">
                    <p className="text-xs text-muted-foreground">Sqft</p>
                    <p className="text-lg font-semibold text-foreground mt-0.5">{fmtNum(selected.squareFeet)}</p>
                  </div>
                  <div className="rounded-lg bg-muted p-3 text-center">
                    <p className="text-xs text-muted-foreground">Built</p>
                    <p className="text-lg font-semibold text-foreground mt-0.5">{selected.yearBuilt ?? '—'}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border bg-card p-5 space-y-0 divide-y divide-border">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground pb-3">Financial</p>
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-teal-400" />
                    <span className="text-sm text-foreground">Estimated Value</span>
                  </div>
                  <span className="text-sm font-semibold text-teal-400">{fmt$(selected.estimatedValue)}</span>
                </div>
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-foreground">Last Sale</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-foreground">{fmt$(selected.lastSalePrice)}</p>
                    {selected.lastSaleDate && (
                      <p className="text-xs text-muted-foreground">{selected.lastSaleDate}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-2">
                    <ArrowRight className="h-4 w-4 text-green-400" />
                    <span className="text-sm text-foreground">Equity</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-green-400">{fmt$(equity(selected))}</p>
                    <p className="text-xs text-muted-foreground">{equityPct(selected)}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-2">
                    <Landmark className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-foreground">Tax Assessment</span>
                  </div>
                  <span className="text-sm text-foreground">{fmt$(selected.taxAssessment)}</span>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-lg border bg-card p-4 space-y-3">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Owner</p>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-teal-500/10 border border-teal-500/20 flex items-center justify-center flex-shrink-0">
                    <User className="h-4 w-4 text-teal-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">{selected.ownerName ?? 'Unknown'}</p>
                    <p className="text-xs text-muted-foreground">{selected.city}, {selected.state}</p>
                  </div>
                </div>
                {selected.taxDelinquent && (
                  <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                    <p className="text-xs font-medium text-red-400">⚠ Tax Delinquent</p>
                    <p className="text-xs text-muted-foreground mt-0.5">High distress signal — prioritize outreach</p>
                  </div>
                )}
              </div>

              <div className="rounded-lg border bg-card p-4 space-y-3">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Actions</p>
                {leadCreated ? (
                  <div className="rounded-lg border border-green-500/20 bg-green-500/10 p-3 text-center">
                    <p className="text-xs font-medium text-green-400">Lead created in pipeline</p>
                  </div>
                ) : (
                  <button
                    onClick={() => createLead(selected)}
                    disabled={creatingLead}
                    className="w-full rounded-lg border border-teal-500/25 bg-teal-500/10 px-4 py-2.5 text-sm font-medium text-teal-400 hover:bg-teal-500/20 transition-colors disabled:opacity-40"
                  >
                    {creatingLead ? 'Creating…' : '+ Add to Lead Pipeline'}
                  </button>
                )}
                <button
                  onClick={() => {
                    const addr = encodeURIComponent(`${selected.address}, ${selected.city}, ${selected.state}`)
                    window.open(`https://www.google.com/maps/search/${addr}`, '_blank')
                  }}
                  className="w-full rounded-lg border border-border px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  View on Google Maps
                </button>
                <button
                  onClick={() => {
                    const addr = encodeURIComponent(`${selected.address}, ${selected.city}, ${selected.state}`)
                    window.open(`https://www.zillow.com/homes/${addr}_rb/`, '_blank')
                  }}
                  className="w-full rounded-lg border border-border px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  View on Zillow
                </button>
              </div>

              <div className="rounded-lg border bg-card p-4 space-y-2">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Raw</p>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ATTOM ID</span>
                    <span className="font-mono text-foreground">{selected.attomId}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Lot size</span>
                    <span className="text-foreground">{selected.lotSize ? `${fmtNum(selected.lotSize)} sqft` : '—'}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  )
}