'use client'

import { useState, useEffect } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { Search, Home, User, DollarSign, Calendar, Landmark, ArrowRight, Bookmark, BookmarkCheck, Calculator, MapPin } from 'lucide-react'
import { apiFetch } from '@/services/api'
import { toast } from 'sonner'

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

interface SavedProperty extends PropertyResult {
  savedAt: string
}

function fmt$(v: number | null): string {
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

function ARVCalculator({ arv }: { arv: number | null }) {
  const [repairCost, setRepairCost] = useState('')
  const [arvOverride, setArvOverride] = useState(arv ? String(arv) : '')

  const arvVal = parseFloat(arvOverride.replace(/[^0-9.]/g, '')) || 0
  const repairVal = parseFloat(repairCost.replace(/[^0-9.]/g, '')) || 0
  const mao70 = arvVal * 0.70 - repairVal
  const mao75 = arvVal * 0.75 - repairVal
  const mao80 = arvVal * 0.80 - repairVal

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3 shadow-card">
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4 text-teal-400" />
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">ARV / MAO Calculator</p>
      </div>
      <div className="space-y-2">
        <div>
          <label className="text-xs text-muted-foreground">ARV ($)</label>
          <input
            type="text"
            value={arvOverride}
            onChange={e => setArvOverride(e.target.value)}
            placeholder="After repair value"
            className="w-full mt-1 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-teal-500/50"
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">Repair cost ($)</label>
          <input
            type="text"
            value={repairCost}
            onChange={e => setRepairCost(e.target.value)}
            placeholder="Estimated repairs"
            className="w-full mt-1 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-teal-500/50"
          />
        </div>
      </div>
      {arvVal > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-border">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">MAO at 70%</span>
            <span className={`font-semibold tabular-nums ${mao70 > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {fmt$(mao70)}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">MAO at 75%</span>
            <span className={`font-semibold tabular-nums ${mao75 > 0 ? 'text-amber-400' : 'text-red-400'}`}>
              {fmt$(mao75)}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">MAO at 80%</span>
            <span className={`font-semibold tabular-nums ${mao80 > 0 ? 'text-blue-400' : 'text-red-400'}`}>
              {fmt$(mao80)}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function PropertiesPage() {
  const [tab, setTab] = useState<'search' | 'saved'>('search')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<PropertyResult[]>([])
  const [selected, setSelected] = useState<PropertyResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [creatingLead, setCreatingLead] = useState(false)
  const [leadCreated, setLeadCreated] = useState(false)
  const [saved, setSaved] = useState<SavedProperty[]>([])

  useEffect(() => {
    const raw = localStorage.getItem('karpathys_saved_properties')
    if (raw) {
      try { setSaved(JSON.parse(raw)) } catch {}
    }
  }, [])

  function saveProperty(prop: PropertyResult) {
    const already = saved.find(s => s.attomId === prop.attomId)
    if (already) {
      toast.info('Already saved')
      return
    }
    const updated = [{ ...prop, savedAt: new Date().toISOString() }, ...saved]
    setSaved(updated)
    localStorage.setItem('karpathys_saved_properties', JSON.stringify(updated))
    toast.success('Property saved')
  }

  function unsaveProperty(attomId: string) {
    const updated = saved.filter(s => s.attomId !== attomId)
    setSaved(updated)
    localStorage.setItem('karpathys_saved_properties', JSON.stringify(updated))
    toast.success('Removed from saved')
  }

  const isSaved = (prop: PropertyResult) => saved.some(s => s.attomId === prop.attomId)

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
          address: prop.address,
          city: prop.city,
          state: prop.state,
          ai_score: prop.taxDelinquent ? 9 : 6,
        }),
      })
      setLeadCreated(true)
      toast.success(`Lead created for ${prop.ownerName ?? prop.address}`)
    } catch {
      toast.error('Failed to create lead')
    } finally {
      setCreatingLead(false)
    }
  }

  function PropertyDetail({ prop }: { prop: PropertyResult }) {
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg border bg-card p-5 shadow-card">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h2 className="text-base font-semibold text-foreground font-display">{prop.address}</h2>
                <p className="text-sm text-muted-foreground mt-0.5">{prop.city}, {prop.state} {prop.zip}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
                {prop.taxDelinquent && (
                  <span className="rounded border border-red-500/20 bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-400">
                    Tax Delinquent
                  </span>
                )}
                <span className="rounded border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                  {prop.propertyType ?? 'Residential'}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: 'Beds', value: prop.bedrooms ?? '—' },
                { label: 'Baths', value: prop.bathrooms ?? '—' },
                { label: 'Sqft', value: fmtNum(prop.squareFeet) },
                { label: 'Built', value: prop.yearBuilt ?? '—' },
              ].map(t => (
                <div key={t.label} className="rounded-lg bg-muted p-3 text-center">
                  <p className="text-xs text-muted-foreground">{t.label}</p>
                  <p className="text-lg font-semibold text-foreground mt-0.5 tabular-nums">{t.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border bg-card p-5 space-y-0 divide-y divide-border shadow-card">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground pb-3">Financial</p>
            {[
              { icon: DollarSign, color: 'text-teal-400', label: 'Estimated Value', value: fmt$(prop.estimatedValue), highlight: true },
              { icon: Calendar, color: 'text-muted-foreground', label: 'Last Sale', value: fmt$(prop.lastSalePrice), sub: prop.lastSaleDate ?? undefined },
              { icon: ArrowRight, color: 'text-green-400', label: 'Equity', value: fmt$(equity(prop)), sub: equityPct(prop) },
              { icon: Landmark, color: 'text-muted-foreground', label: 'Tax Assessment', value: fmt$(prop.taxAssessment) },
            ].map(row => (
              <div key={row.label} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-2">
                  <row.icon className={`h-4 w-4 ${row.color}`} />
                  <span className="text-sm text-foreground">{row.label}</span>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-semibold ${row.highlight ? 'text-teal-400' : 'text-foreground'}`}>{row.value}</p>
                  {row.sub && <p className="text-xs text-muted-foreground">{row.sub}</p>}
                </div>
              </div>
            ))}
          </div>

          <ARVCalculator arv={prop.estimatedValue} />
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4 space-y-3 shadow-card">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Owner</p>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-teal-500/10 border border-teal-500/20 flex items-center justify-center flex-shrink-0">
                <User className="h-4 w-4 text-teal-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">{prop.ownerName ?? 'Unknown'}</p>
                <p className="text-xs text-muted-foreground">{prop.city}, {prop.state}</p>
              </div>
            </div>
            {prop.taxDelinquent && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                <p className="text-xs font-medium text-red-400">⚠ Tax Delinquent</p>
                <p className="text-xs text-muted-foreground mt-0.5">High distress signal — prioritize outreach</p>
              </div>
            )}
          </div>

          <div className="rounded-lg border bg-card p-4 space-y-2 shadow-card">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Actions</p>
            {leadCreated ? (
              <div className="rounded-lg border border-green-500/20 bg-green-500/10 p-3 text-center">
                <p className="text-xs font-medium text-green-400">✓ Lead created in pipeline</p>
              </div>
            ) : (
              <button
                onClick={() => createLead(prop)}
                disabled={creatingLead}
                className="w-full rounded-lg border border-teal-500/25 bg-teal-500/10 px-4 py-2.5 text-sm font-medium text-teal-400 hover:bg-teal-500/20 transition-colors disabled:opacity-40"
              >
                {creatingLead ? 'Creating…' : '+ Add to Lead Pipeline'}
              </button>
            )}
            <button
              onClick={() => isSaved(prop) ? unsaveProperty(prop.attomId) : saveProperty(prop)}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              {isSaved(prop)
                ? <><BookmarkCheck className="h-4 w-4 text-teal-400" /> Saved</>
                : <><Bookmark className="h-4 w-4" /> Save property</>
              }
            </button>
            <button
              onClick={() => {
                const addr = encodeURIComponent(`${prop.address}, ${prop.city}, ${prop.state}`)
                window.open(`https://www.google.com/maps/search/${addr}`, '_blank')
              }}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <MapPin className="h-4 w-4" /> View on Maps
            </button>
            <button
              onClick={() => {
                const addr = encodeURIComponent(`${prop.address}, ${prop.city}, ${prop.state}`)
                window.open(`https://www.zillow.com/homes/${addr}_rb/`, '_blank')
              }}
              className="w-full rounded-lg border border-border px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              View on Zillow
            </button>
          </div>

          <div className="rounded-lg border bg-card p-4 space-y-2 shadow-card">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Raw</p>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">ID</span>
                <span className="font-mono text-foreground">{prop.attomId.slice(0, 12)}…</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Lot size</span>
                <span className="text-foreground">{prop.lotSize ? `${fmtNum(prop.lotSize)} sqft` : '—'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <PageContainer title="Properties" description="Search, analyze, and save properties for acquisition">
      <div className="space-y-4 max-w-content">
        <div className="flex gap-2 border-b border-border pb-4">
          {(['search', 'saved'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === t
                  ? 'bg-teal-500/10 text-teal-400 border border-teal-500/25'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t === 'search' ? 'Search' : `Saved (${saved.length})`}
            </button>
          ))}
        </div>

        {tab === 'search' && (
          <>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && search()}
                  placeholder="1234 Main St, Stockton CA"
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
                <p className="text-xs text-muted-foreground mt-1 opacity-60">Owner info, AVM, tax records, equity analysis</p>
              </div>
            )}

            {results.length > 1 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">{results.length} results</p>
                {results.map(r => (
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

            {selected && <PropertyDetail prop={selected} />}
          </>
        )}

        {tab === 'saved' && (
          <div className="space-y-4">
            {saved.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-12 text-center">
                <Bookmark className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-40" />
                <p className="text-sm text-muted-foreground">No saved properties yet</p>
                <p className="text-xs text-muted-foreground mt-1 opacity-60">Search an address and click Save property</p>
              </div>
            ) : (
              saved.map(prop => (
                <div key={prop.attomId} className="rounded-lg border bg-card shadow-card p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground font-display">{prop.address}</p>
                      <p className="text-xs text-muted-foreground">{prop.city}, {prop.state} {prop.zip}</p>
                    </div>
                    <button
                      onClick={() => unsaveProperty(prop.attomId)}
                      className="text-muted-foreground hover:text-red-400 transition-colors flex-shrink-0"
                    >
                      <BookmarkCheck className="h-4 w-4 text-teal-400" />
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="rounded bg-muted p-2 text-center">
                      <p className="text-muted-foreground">Value</p>
                      <p className="font-semibold text-teal-400 mt-0.5">{fmt$(prop.estimatedValue)}</p>
                    </div>
                    <div className="rounded bg-muted p-2 text-center">
                      <p className="text-muted-foreground">Equity</p>
                      <p className="font-semibold text-green-400 mt-0.5">{equityPct(prop)}</p>
                    </div>
                    <div className="rounded bg-muted p-2 text-center">
                      <p className="text-muted-foreground">Score</p>
                      <p className={`font-semibold mt-0.5 ${prop.taxDelinquent ? 'text-red-400' : 'text-foreground'}`}>
                        {prop.taxDelinquent ? 'Delinquent' : 'Clean'}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => { setTab('search'); setSelected(prop); setResults([prop]) }}
                    className="w-full rounded-md border border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    View full details
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </PageContainer>
  )
}