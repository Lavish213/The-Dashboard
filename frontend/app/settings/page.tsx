'use client'

import Link from 'next/link'
import { useState } from 'react'
import { PageContainer } from '@/components/workspace/PageContainer'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth.store'
import { useTheme } from '@/hooks/ui/useTheme'
import { logout } from '@/services/auth'

const tabs = ['Sophia', 'Notifications', 'Users', 'Security'] as const

export default function SettingsPage() {
  const user = useAuthStore(s => s.user)
  const { isDark, toggleTheme, mounted } = useTheme()
  const [signingOut, setSigningOut] = useState(false)

  return (
    <PageContainer title="Settings" description="Your workspace preferences and configuration status">
      <div className="max-w-3xl space-y-6">
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
            <p className="text-sm text-muted-foreground">The server does not currently expose voice configuration to this dashboard. Model, speech providers, approval policy and cost limits cannot be verified or changed here.</p>
            <Link href="/realtime" className="inline-block text-sm font-medium text-foreground underline underline-offset-4">Open Sophia live</Link>
          </TabsContent>
          <TabsContent value="Notifications" className="rounded-lg border bg-card p-5 space-y-3">
            <h2 className="text-lg font-semibold">Notification preferences unavailable</h2>
            <p className="text-sm text-muted-foreground">Notification delivery and escalation preferences are not connected to a settings API.</p>
            <Link href="/approvals" className="inline-block text-sm font-medium text-foreground underline underline-offset-4">Review pending approvals</Link>
          </TabsContent>
          <TabsContent value="Users" className="rounded-lg border bg-card p-5 space-y-3">
            <h2 className="text-lg font-semibold">Signed-in account</h2>
            {user ? <dl className="grid gap-3 text-sm">
              <div><dt className="text-muted-foreground">Name</dt><dd className="break-words">{user.name}</dd></div>
              <div><dt className="text-muted-foreground">Email</dt><dd className="break-words">{user.email}</dd></div>
              <div><dt className="text-muted-foreground">Role</dt><dd>{user.role}</dd></div>
            </dl> : <p className="text-sm text-muted-foreground">Account information unavailable.</p>}
            <p className="text-sm text-muted-foreground">Team administration is not connected here.</p>
            <Button variant="outline" disabled={signingOut} onClick={async () => { setSigningOut(true); await logout() }}>{signingOut ? 'Signing out…' : 'Sign out'}</Button>
          </TabsContent>
          <TabsContent value="Security" className="rounded-lg border bg-card p-5 space-y-3">
            <h2 className="text-lg font-semibold">Server-managed security</h2>
            <p className="text-sm text-muted-foreground">Token lifetimes and session policy are managed by the server. This dashboard does not expose their configured values.</p>
            <Link href="/audit" className="inline-block text-sm font-medium text-foreground underline underline-offset-4">Open audit log</Link>
          </TabsContent>
        </Tabs>
      </div>
    </PageContainer>
  )
}
