import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Sign In' }

export default function LoginPage() {
  return (
    <div className="w-full max-w-sm space-y-6 rounded-lg border border-border bg-card p-8">
      <div className="space-y-1.5 text-center">
        <div className="mx-auto mb-4 flex h-8 w-8 items-center justify-center rounded-md bg-primary">
          <span className="text-sm font-bold text-primary-foreground">K</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          Sign in to Karpathys
        </h1>
        <p className="text-sm text-muted-foreground">
          Operational control platform
        </p>
      </div>

      {/* Phase 3 — auth form implemented with backend */}
      <div className="space-y-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            placeholder="agent@karpathys.io"
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            autoComplete="email"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            autoComplete="current-password"
          />
        </div>
        <button
          type="button"
          className="h-9 w-full rounded-md bg-primary text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
        >
          Sign in
        </button>
      </div>

      <p className="text-center text-[10px] text-muted-foreground">
        Authentication enforced in Phase 3
      </p>
    </div>
  )
}
