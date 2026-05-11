'use client'

import * as React from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { useNavigation } from '@/hooks/navigation/useNavigation'
import { NAV_ROUTES } from '@/lib/navigation/routes'

/** Mobile bottom nav shows the top 5 primary routes */
const BOTTOM_NAV_ROUTE_IDS = ['dashboard', 'leads', 'calls', 'approvals', 'settings']

export function BottomNav() {
  const { isActive } = useNavigation()
  const routes = NAV_ROUTES.filter((r) => BOTTOM_NAV_ROUTE_IDS.includes(r.id))

  return (
    <nav
      aria-label="Bottom navigation"
      className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center border-t border-border bg-background pb-safe md:hidden"
    >
      {routes.map((route) => {
        const Icon = route.icon
        const active = isActive(route.href)

        return (
          <Link
            key={route.id}
            href={route.href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'flex flex-1 flex-col items-center justify-center gap-0.5 py-2',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
              active ? 'text-primary' : 'text-muted-foreground'
            )}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
            <span className="text-[10px] font-medium">{route.label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
