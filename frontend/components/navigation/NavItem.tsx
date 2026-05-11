'use client'

import * as React from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import type { NavRoute } from '@/lib/navigation/routes'

interface NavItemProps {
  route: NavRoute
  active: boolean
  collapsed: boolean
  badge?: number
}

export function NavItem({ route, active, collapsed, badge }: NavItemProps) {
  const Icon = route.icon

  return (
    <Link
      href={route.href}
      aria-current={active ? 'page' : undefined}
      title={collapsed ? route.label : undefined}
      className={cn(
        'group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        active
          ? 'bg-primary/10 text-primary font-medium'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        collapsed && 'justify-center px-0'
      )}
    >
      <Icon
        className={cn(
          'h-4 w-4 flex-shrink-0 transition-colors',
          active ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
        )}
        aria-hidden="true"
      />
      {!collapsed && (
        <>
          <span className="flex-1 truncate">{route.label}</span>
          {badge !== undefined && badge > 0 && (
            <span
              className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground"
              aria-label={`${badge} pending`}
            >
              {badge > 99 ? '99+' : badge}
            </span>
          )}
        </>
      )}
    </Link>
  )
}
