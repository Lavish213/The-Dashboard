'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { NavItem } from './NavItem'
import { NAV_ROUTES, NAV_GROUPS, type NavGroup } from '@/lib/navigation/routes'
import { useNavigation } from '@/hooks/navigation/useNavigation'
import { useApprovalStore } from '@/stores/approval.store'

interface AppNavProps {
  collapsed?: boolean
  onCollapseToggle?: () => void
  className?: string
}

/**
 * AppNav — full sidebar navigation with route-awareness, group headers, and badge support.
 * Reads active route from useNavigation; badge counts from stores.
 */
export function AppNav({ collapsed = false, onCollapseToggle, className }: AppNavProps) {
  const { isActive } = useNavigation()
  const approvalsPending = useApprovalStore((s) => s.pendingCount)

  const badgeMap: Record<string, number | undefined> = {
    approvals: approvalsPending || undefined,
  }

  const routesByGroup = (group: NavGroup) =>
    NAV_ROUTES.filter((r) => r.group === group)

  return (
    <nav
      aria-label="Main navigation"
      className={cn('flex h-full flex-col overflow-hidden', className)}
    >
      {/* Logo / wordmark */}
      <div
        className={cn(
          'flex flex-shrink-0 items-center border-b border-border',
          collapsed ? 'justify-center px-1.5 py-3' : 'gap-2 px-4 py-3'
        )}
      >
        <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md bg-primary">
          <span className="text-[10px] font-bold text-primary-foreground">K</span>
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold tracking-tight text-foreground">
            Karpathys
          </span>
        )}
      </div>

      {/* Nav groups */}
      <div className="flex-1 overflow-y-auto py-2 scrollbar-thin">
        {NAV_GROUPS.map((group) => {
          const routes = routesByGroup(group.id)
          if (!routes.length) return null
          return (
            <div key={group.id} className="mb-3">
              {!collapsed && (
                <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
                  {group.label}
                </p>
              )}
              <ul className="space-y-0.5 px-1.5" role="list">
                {routes.map((route) => (
                  <li key={route.id}>
                    <NavItem
                      route={route}
                      active={isActive(route.href)}
                      collapsed={collapsed}
                      badge={route.badgeKey ? badgeMap[route.id] : undefined}
                    />
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>

      {/* Collapse toggle */}
      {onCollapseToggle && (
        <div className="flex-shrink-0 border-t border-border p-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCollapseToggle}
            className={cn(
              'w-full',
              collapsed ? 'justify-center px-0' : 'justify-between'
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {!collapsed && (
              <span className="text-xs text-muted-foreground">Collapse</span>
            )}
            <ChevronLeft
              className={cn(
                'h-4 w-4 flex-shrink-0 transition-transform duration-200',
                collapsed && 'rotate-180'
              )}
            />
          </Button>
        </div>
      )}
    </nav>
  )
}
