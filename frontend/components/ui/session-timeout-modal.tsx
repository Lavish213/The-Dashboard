'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuthStore } from '@/stores/auth.store'

const WARNING_BEFORE_MS = 5 * 60 * 1000
const CHECK_INTERVAL_MS = 30 * 1000

function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

export function SessionTimeoutModal() {
  const { token, clearUser } = useAuthStore()
  const [showWarning, setShowWarning] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(0)

  const logout = useCallback(() => {
    clearUser()
    window.location.replace('/login')
  }, [clearUser])

  useEffect(() => {
    if (!token) return

    let warningTimer: ReturnType<typeof setTimeout> | null = null
    let countdownInterval: ReturnType<typeof setInterval> | null = null

    function schedule() {
      const expiry = getTokenExpiry(token!)
      if (!expiry) return

      const now = Date.now()
      const msUntilExpiry = expiry - now
      const msUntilWarning = msUntilExpiry - WARNING_BEFORE_MS

      if (msUntilExpiry <= 0) {
        logout()
        return
      }

      if (warningTimer) clearTimeout(warningTimer)

      if (msUntilWarning <= 0) {
        setShowWarning(true)
        setSecondsLeft(Math.max(0, Math.round(msUntilExpiry / 1000)))
      } else {
        warningTimer = setTimeout(() => {
          setShowWarning(true)
          setSecondsLeft(Math.round(WARNING_BEFORE_MS / 1000))
        }, msUntilWarning)
      }
    }

    schedule()
    const checkTimer = setInterval(schedule, CHECK_INTERVAL_MS)

    return () => {
      if (warningTimer) clearTimeout(warningTimer)
      if (countdownInterval) clearInterval(countdownInterval)
      clearInterval(checkTimer)
    }
  }, [token, logout])

  useEffect(() => {
    if (!showWarning) return

    const interval = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          logout()
          return 0
        }
        return s - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [showWarning, logout])

  if (!showWarning) return null

  const minutes = Math.floor(secondsLeft / 60)
  const seconds = secondsLeft % 60
  const timeLabel = minutes > 0
    ? `${minutes}m ${String(seconds).padStart(2, '0')}s`
    : `${secondsLeft}s`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-lg border border-border bg-card p-6 shadow-2xl space-y-4 mx-4">
        <div className="space-y-1">
          <h2 className="text-sm font-semibold text-foreground">Session expiring</h2>
          <p className="text-xs text-muted-foreground">
            Your session will expire in{' '}
            <span className="font-semibold tabular-nums text-amber-400">{timeLabel}</span>.
            You will be signed out automatically.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={logout}
            className="flex-1 rounded-md border border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            Sign out now
          </button>
          <button
            onClick={() => setShowWarning(false)}
            className="flex-1 rounded-md border border-teal-500/25 bg-teal-500/10 px-3 py-2 text-xs font-medium text-teal-400 hover:bg-teal-500/20 transition-colors"
          >
            Stay signed in
          </button>
        </div>
      </div>
    </div>
  )
}