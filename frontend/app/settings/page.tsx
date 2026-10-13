'use client'

import Link from 'next/link'
import { useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth.store'
import { useTheme } from '@/hooks/ui/useTheme'
import { logout } from '@/services/auth'
import { NotificationFeed, TeamRoster, useServerConfiguration } from '@/components/settings/ServerSettings'

const tabs = ['Sophia', 'Notifications', 'Users', 'Security'] as const

export default function SettingsPage() {
  const user = useAuthStore(s => s.user)
  const { isDark, toggleTheme, mounted } = useTheme()
  const [signingOut, setSigningOut] = useState(false)
  const configuration = useServerConfiguration()

  return (
    <PageContainer title="Settings" description="Your workspace preferences and configuration status">
      <div className="max-w-3xl space-y-6">
        {configuration.isPending && <p role="status" className="text-sm text-muted-foreground">Loading server configuration…</p>}
        {configuration.isError && <p role="alert" className="text-sm text-destructive">Server configuration unavailable. Configuration values cannot be verified.</p>}
        {configuration.data && <p className="text-xs text-muted-foreground">Dashboard server · {configuration.data.environment} · Version {configuration.data.app_version}{configuration.isError ? ' · May be stale' : ''}</p>}
        <section className="flex flex-wrap items-center justify-between gap-4 rounded-lg border bg-card p-5" aria-labelledby="appearance-heading">
          <div>
            <h2 id="appearance-heading" className="text-base font-semibold">Appearance</h2>
            <p className="mt-1 text-sm text-muted-foreground">Saved in this browser.</p>
          </div>
          {mounted && <Button variant="outline" onClick={toggleTheme}>{isDark ? 'Use light theme' : 'Use dark theme'}</Button>}
        </section>
        <Tabs defaultValue="Sophia">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-1 sm:grid-cols-4" aria-label="Settings categories">
            {tabs.map(tab => <TabsTrigger key={tab} value={tab}>{tab}</TabsTrigger>)}
          </TabsList>
          <TabsContent value="Sophia" className="rounded-lg border bg-card p-5 space-y-3">
            <h2 className="text-lg font-semibold">Voice configuration</h2>
            <p className="text-sm text-muted-foreground">{configuration.data?.voice_configuration.reason ?? 'Voice configuration is unavailable. Model, providers, approval policy and cost limits cannot be verified or changed here.'}</p>
            <Link href="/realtime" className="inline-block text-sm font-medium text-foreground underline underline-offset-4">Open Sophia live</Link>
          </TabsContent>
          <TabsContent value="Notifications" className="rounded-lg border bg-card p-5 space-y-3">
            <NotificationFeed />
            <Link href="/approvals" className="inline-block text-sm font-medium text-foreground underline underline-offset-4">Review pending approvals</Link>
          </TabsContent>
          <TabsContent value="Users" className="rounded-lg border bg-card p-5 space-y-3">
            <h2 className="text-lg font-semibold">Signed-in account</h2>
            {user ? <dl className="grid gap-3 text-sm">
              <div><dt className="text-muted-foreground">Name</dt><dd className="break-words">{user.name}</dd></div>
              <div><dt className="text-muted-foreground">Email</dt><dd className="break-words">{user.email}</dd></div>
              <div><dt className="text-muted-foreground">Role</dt><dd>{user.role}</dd></div>
            </dl> : <p className="text-sm text-muted-foreground">Account information unavailable.</p>}
            <Button variant="outline" disabled={signingOut} onClick={async () => { setSigningOut(true); await logout() }}>{signingOut ? 'Signing out…' : 'Sign out'}</Button>
            <TeamRoster />
          </TabsContent>
          <TabsContent value="Security" className="rounded-lg border bg-card p-5 space-y-3">
            <h2 className="text-lg font-semibold">Server-managed security</h2>
            <p className="text-sm text-muted-foreground">Read-only values reported by the dashboard server.</p>
            {configuration.data && <dl className="space-y-2 text-sm"><div><dt className="text-muted-foreground">Access token lifetime</dt><dd>{configuration.data.security.access_token_minutes} minutes</dd></div><div><dt className="text-muted-foreground">Refresh token lifetime</dt><dd>{configuration.data.security.refresh_token_days} days</dd></div></dl>}
            <Link href="/audit" className="inline-block text-sm font-medium text-foreground underline underline-offset-4">Open audit log</Link>
          </TabsContent>
        </Tabs>
      </div>
    </PageContainer>
  )
}
