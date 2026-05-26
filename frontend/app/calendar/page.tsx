'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { PageContainer } from '@/components/workspace/PageContainer'
import { apiFetch } from '@/services/api'
import { toast } from 'sonner'
import { LeadAvatar } from '@/components/leads/LeadAvatar'
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Lead {
  id: string
  full_name: string
  phone: string | null
  lead_status: string
  ai_score: number | null
  follow_up_at: string | null
}

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year: number, month: number) {
  return new Date(year, month, 1).getDay()
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export default function CalendarPage() {
  const router = useRouter()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDay, setSelectedDay] = useState<number | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch<{ items: Lead[] }>('/api/v1/leads?page_size=200')
        setLeads(data.items.filter(l => l.follow_up_at))
      } catch {
        toast.error('Failed to load calendar')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  function prevMonth() {
    if (month === 0) { setMonth(11); setYear(y => y - 1) }
    else setMonth(m => m - 1)
    setSelectedDay(null)
  }

  function nextMonth() {
    if (month === 11) { setMonth(0); setYear(y => y + 1) }
    else setMonth(m => m + 1)
    setSelectedDay(null)
  }

  const daysInMonth = getDaysInMonth(year, month)
  const firstDay = getFirstDayOfMonth(year, month)

  function leadsForDay(day: number): Lead[] {
    return leads.filter(l => {
      if (!l.follow_up_at) return false
      const d = new Date(l.follow_up_at)
      return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day
    })
  }

  const selectedLeads = selectedDay ? leadsForDay(selectedDay) : []
  const today = now.getFullYear() === year && now.getMonth() === month ? now.getDate() : null

  return (
    <PageContainer title="Calendar" description="Follow-up schedule and appointments">
      <div className="space-y-4 max-w-content">
        <div className="rounded-lg border bg-card shadow-card p-4">
          <div className="flex items-center justify-between mb-4">
            <Button variant="ghost" size="sm" onClick={prevMonth} className="h-8 w-8 p-0">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <p className="text-sm font-semibold text-foreground font-display">
              {MONTH_NAMES[month]} {year}
            </p>
            <Button variant="ghost" size="sm" onClick={nextMonth} className="h-8 w-8 p-0">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid grid-cols-7 gap-1 mb-2">
            {DAY_NAMES.map(d => (
              <div key={d} className="text-center text-xs text-muted-foreground py-1">
                {d}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {[...Array(firstDay)].map((_, i) => (
              <div key={`empty-${i}`} />
            ))}
            {[...Array(daysInMonth)].map((_, i) => {
              const day = i + 1
              const dayLeads = leadsForDay(day)
              const isToday = today === day
              const isSelected = selectedDay === day

              return (
                <button
                  key={day}
                  onClick={() => setSelectedDay(isSelected ? null : day)}
                  className={`relative rounded-md p-1.5 text-center text-xs transition-all min-h-[36px] ${
                    isSelected
                      ? 'bg-teal-500/20 border border-teal-500/40 text-teal-400'
                      : isToday
                      ? 'bg-teal-500/10 border border-teal-500/20 text-teal-400 font-semibold'
                      : 'hover:bg-muted text-foreground'
                  }`}
                >
                  {day}
                  {dayLeads.length > 0 && (
                    <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 flex gap-0.5">
                      {dayLeads.slice(0, 3).map((_, idx) => (
                        <span key={idx} className="h-1 w-1 rounded-full bg-teal-400" />
                      ))}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {selectedDay && (
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
              {MONTH_NAMES[month]} {selectedDay} — {selectedLeads.length} follow-up{selectedLeads.length !== 1 ? 's' : ''}
            </p>
            {selectedLeads.length === 0 ? (
              <div className="rounded-lg border bg-card p-6 text-center">
                <CalendarDays className="h-6 w-6 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No follow-ups scheduled</p>
              </div>
            ) : (
              selectedLeads.map(lead => (
                <div
                  key={lead.id}
                  onClick={() => router.push(`/leads/${lead.id}`)}
                  className="flex items-center gap-3 rounded-lg border bg-card shadow-card px-4 py-3 cursor-pointer hover:border-teal-500/30 transition-all"
                >
                  <LeadAvatar name={lead.full_name} score={lead.ai_score} size="sm" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{lead.full_name}</p>
                    {lead.phone && (
                      <p className="text-xs text-muted-foreground font-mono">{lead.phone}</p>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground">{lead.lead_status}</span>
                </div>
              ))
            )}
          </div>
        )}

        {!loading && !selectedDay && (
          <div className="rounded-lg border bg-card p-6 text-center shadow-card">
            <p className="text-xs text-muted-foreground">
              Click a day to see scheduled follow-ups
            </p>
          </div>
        )}
      </div>
    </PageContainer>
  )
}