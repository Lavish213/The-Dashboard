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
      <div
        className={cn(
          'flex flex-shrink-0 items-center border-b border-border',
          collapsed ? 'justify-center px-1.5 py-3' : 'gap-2.5 px-4 py-3'
        )}
      >
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-teal-500/15 border border-teal-500/30">
          <span className="text-[11px] font-bold text-teal-400 font-display">K</span>
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <span className="text-sm font-semibold tracking-tight text-foreground font-display">
              Karpathys
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {NAV_GROUPS.map((group) => {
          const routes = routesByGroup(group.id)
          if (!routes.length) return null
          return (
            <div key={group.id} className="mb-4">
              {!collapsed && (
                <p className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50">
                  {group.label}
                </p>
              )}
              {collapsed && (
                <div className="mx-auto mb-1.5 h-px w-6 bg-border" />
              )}
              <ul className="space-y-0.5 px-2" role="list">
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

      {onCollapseToggle && (
        <div className="flex-shrink-0 border-t border-border p-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCollapseToggle}
            className={cn(
              'w-full h-8 text-muted-foreground hover:text-foreground',
              collapsed ? 'justify-center px-0' : 'justify-between px-2'
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {!collapsed && (
              <span className="text-xs">Collapse</span>
            )}
            <ChevronLeft
              className={cn(
                'h-3.5 w-3.5 flex-shrink-0 transition-transform duration-200',
                collapsed && 'rotate-180'
              )}
            />
          </Button>
        </div>
      )}
    </nav>
  )
}