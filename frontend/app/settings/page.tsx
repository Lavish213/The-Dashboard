'use client'

import { useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'

const TABS = ['Sophia', 'Notifications', 'Users', 'Security'] as const
type Tab = typeof TABS[number]

function SettingRow({ label, description, value, toggle }: {
  label: string
  description: string
  value?: string
  toggle?: boolean
}) {
  const [on, setOn] = useState(true)
  return (
    <div className="flex items-center gap-4 py-3 border-b border-border last:border-0">
      <div className="flex-1">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
      {value && (
        <span className="rounded border border-teal-500/20 bg-teal-500/10 px-2.5 py-1 text-xs text-teal-400 font-medium">
          {value}
        </span>
      )}
      {toggle && (
        <button
          onClick={() => setOn(!on)}
          className={`relative w-9 h-5 rounded-full transition-colors ${on ? 'bg-teal-500' : 'bg-muted'}`}
        >
          <span className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white transition-transform ${on ? 'translate-x-4' : ''}`} />
        </button>
      )}
    </div>
  )
}

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>('Sophia')

  return (
    <PageContainer title="Settings" description="System configuration and preferences">
      <div className="flex gap-1 mb-6 bg-card border border-border rounded-lg p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-xs font-medium transition-colors ${tab === t ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Sophia' && (
        <div className="rounded-lg border bg-card p-4 space-y-0">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-2">Voice agent</p>
          <SettingRow label="LLM model" description="Primary language model powering Sophia" value="claude-sonnet-4-6" />
          <SettingRow label="STT provider" description="Speech-to-text transcription engine" value="Deepgram Nova-2" />
          <SettingRow label="TTS provider" description="Voice synthesis for Sophia responses" value="ElevenLabs" />
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-2 mt-4">Behavior</p>
          <SettingRow label="Require offer approval" description="All offers must pass approval gate before dispatch" toggle />
          <SettingRow label="Auto-confirm appointments" description="Skip approval gate for appointment confirmations" toggle />
          <SettingRow label="Max cost per call" description="Hard ceiling — call terminates at this amount" value="$8.00" />
        </div>
      )}

      {tab === 'Notifications' && (
        <div className="rounded-lg border bg-card p-4">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-2">Alerts</p>
          <SettingRow label="Call failure alerts" description="Notify when call failure rate exceeds threshold" toggle />
          <SettingRow label="Cost threshold alerts" description="Notify when daily cost exceeds limit" toggle />
          <SettingRow label="Approval escalation" description="Notify when approvals are approaching expiry" toggle />
        </div>
      )}

      {tab === 'Users' && (
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Team members</p>
          </div>
          <div className="flex items-center gap-3 py-3 border-b border-border">
            <div className="h-8 w-8 rounded-full bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-xs font-semibold text-teal-400">AA</div>
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">Angelo Alcarez</p>
              <p className="text-xs text-muted-foreground">admin@karpathys.dev</p>
            </div>
            <span className="rounded border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground">Admin</span>
          </div>
        </div>
      )}

      {tab === 'Security' && (
        <div className="rounded-lg border bg-card p-4">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-2">Authentication</p>
          <SettingRow label="JWT token expiry" description="Access token lifetime" value="24 hours" />
          <SettingRow label="Refresh token expiry" description="Refresh token lifetime" value="7 days" />
          <SettingRow label="Session timeout warning" description="Warn before session expires" toggle />
        </div>
      )}
    </PageContainer>
  )
}