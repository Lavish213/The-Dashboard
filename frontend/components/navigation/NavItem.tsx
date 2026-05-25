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
        'group relative flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-all duration-100',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        active
          ? 'bg-teal-500/10 text-teal-400 font-medium border-l-2 border-teal-400 pl-[6px]'
          : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground border-l-2 border-transparent pl-[6px]',
        collapsed && 'justify-center px-0 pl-0 border-l-0'
      )}
    >
      <Icon
        className={cn(
          'h-4 w-4 flex-shrink-0 transition-colors',
          active ? 'text-teal-400' : 'text-muted-foreground group-hover:text-foreground'
        )}
        aria-hidden="true"
      />
      {!collapsed && (
        <>
          <span className="flex-1 truncate">{route.label}</span>
          {badge !== undefined && badge > 0 && (
            <span
              className="flex h-4 min-w-4 items-center justify-center rounded-full bg-teal-500/20 px-1 text-[10px] font-semibold text-teal-400"
              aria-label={`${badge} pending`}
            >
              {badge > 99 ? '99+' : badge}
            </span>
          )}
        </>
      )}

      {collapsed && active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-teal-400 rounded-r" />
      )}
    </Link>
  )
}