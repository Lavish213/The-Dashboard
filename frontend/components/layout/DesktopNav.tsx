import * as React from 'react'
import { cn } from '@/lib/utils'
import type { SidebarNavItem } from './Sidebar'

interface DesktopNavProps {
  items: SidebarNavItem[]
  orientation?: 'horizontal' | 'vertical'
  className?: string
}

/**
 * DesktopNav — horizontal top nav for lg+ screens.
 * Used in non-dashboard layouts where a horizontal nav bar is preferred.
 */
export function DesktopNav({
  items,
  orientation = 'horizontal',
  className,
}: DesktopNavProps) {
  return (
    <nav
      aria-label="Desktop navigation"
      className={cn(
        orientation === 'horizontal' ? 'hidden md:flex items-center gap-1' : 'flex flex-col gap-0.5',
        className
      )}
    >
      {items.map((item) => (
        <a
          key={item.id}
          href={item.href ?? '#'}
          className={cn(
            'flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors',
            'text-muted-foreground hover:bg-muted hover:text-foreground',
            item.active && 'bg-primary/10 text-primary font-medium'
          )}
          aria-current={item.active ? 'page' : undefined}
        >
          {item.icon && (
            <span className="h-4 w-4 flex items-center justify-center">
              {item.icon}
            </span>
          )}
          <span>{item.label}</span>
          {item.badge !== undefined && (
            <span className="ml-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary/15 px-1 text-[10px] font-medium text-primary">
              {item.badge}
            </span>
          )}
        </a>
      ))}
    </nav>
  )
}
