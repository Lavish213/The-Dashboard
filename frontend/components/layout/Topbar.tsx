'use client'

import * as React from 'react'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/hooks/ui/useTheme'
import { apiFetch } from '@/services/api'

function ConnectionDot() {
  const [connected, setConnected] = useState(true)

  useEffect(() => {
    async function check() {
      try {
        await apiFetch('/api/ready')
        setConnected(true)
      } catch {
        setConnected(false)
      }
    }
    check()
    const id = setInterval(check, 15_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex items-center gap-1.5 px-2">
      <div
        className={cn(
          'h-1.5 w-1.5 rounded-full flex-shrink-0',
          connected ? 'bg-green-400' : 'bg-red-400 animate-pulse'
        )}
      />
      {!connected && (
        <span className="text-xs text-red-400">Offline</span>
      )}
    </div>
  )
}

interface TopbarProps {
  left?: React.ReactNode
  center?: React.ReactNode
  right?: React.ReactNode
  showThemeToggle?: boolean
  className?: string
}

export function Topbar({
  left,
  center,
  right,
  showThemeToggle = true,
  className,
}: TopbarProps) {
  const { toggleTheme, isDark, mounted } = useTheme()

  return (
    <div className={cn('flex h-full items-center gap-3 px-4', className)}>
      {left && <div className="flex items-center gap-2 min-w-0 flex-1">{left}</div>}
      {!left && <div className="flex-1" />}

      {center && (
        <div className="flex items-center justify-center gap-2">{center}</div>
      )}

      <div className="flex items-center gap-1">
        <ConnectionDot />
        {right}
        {showThemeToggle && mounted && (
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            className="h-8 w-8 p-0"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>
    </div>
  )
}