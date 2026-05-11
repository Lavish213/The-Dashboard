'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/hooks/ui/useTheme'

interface TopbarProps {
  /** Left slot: breadcrumbs, page title */
  left?: React.ReactNode
  /** Center slot */
  center?: React.ReactNode
  /** Right slot: user menu, notifications, etc. */
  right?: React.ReactNode
  /** Show theme toggle */
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
    <div
      className={cn(
        'flex h-full items-center gap-3 px-4',
        className
      )}
    >
      {/* Left */}
      {left && <div className="flex items-center gap-2 min-w-0 flex-1">{left}</div>}
      {!left && <div className="flex-1" />}

      {/* Center */}
      {center && (
        <div className="flex items-center justify-center gap-2">{center}</div>
      )}

      {/* Right */}
      <div className="flex items-center gap-1.5">
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
