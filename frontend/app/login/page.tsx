'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { login } from '@/services/auth'

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const form = e.currentTarget
    const email = (form.elements.namedItem('email') as HTMLInputElement).value
    const password = (form.elements.namedItem('password') as HTMLInputElement).value

    try {
      await login({ email, password })
      router.push('/dashboard')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Sign-in unavailable. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-sm space-y-6 rounded-lg border border-border bg-card p-8">
      <div className="space-y-1.5 text-center">
        <div className="mx-auto mb-4 flex h-8 w-8 items-center justify-center rounded-md bg-primary">
          <span className="text-sm font-bold text-primary-foreground">K</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          Sign in to Karpathys
        </h1>
        <p className="text-sm text-muted-foreground">Operational control platform</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            placeholder="agent@karpathys.io"
            autoComplete="email"
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            placeholder="••••••••"
            autoComplete="current-password"
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        {error && (
          <p role="alert" className="text-sm text-destructive">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="h-9 w-full rounded-md bg-primary text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="text-center text-[10px] text-muted-foreground">
        Use your workspace account to sign in.
      </p>
    </div>
  )
}
