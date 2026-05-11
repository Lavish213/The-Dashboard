'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface SidebarNavItem {
  id: string
  label: string
  icon?: React.ReactNode
  href?: string
  badge?: string | number
  children?: SidebarNavItem[]
  /** Active state */
  active?: boolean
}

interface SidebarProps {
  items?: SidebarNavItem[]
  header?: React.ReactNode
  footer?: React.ReactNode
  collapsed?: boolean
  onCollapseToggle?: () => void
  className?: string
  children?: React.ReactNode
}

function NavItem({
  item,
  collapsed,
  depth = 0,
}: {
  item: SidebarNavItem
  collapsed: boolean
  depth?: number
}) {
  const [open, setOpen] = React.useState(false)
  const hasChildren = item.children && item.children.length > 0

  return (
    <li>
      <a
        href={item.href ?? '#'}
        className={cn(
          'flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors',
          'text-muted-foreground hover:bg-muted hover:text-foreground',
          item.active && 'bg-primary/10 text-primary font-medium',
          collapsed && 'justify-center px-0',
          depth > 0 && 'ml-6 text-xs'
        )}
        onClick={hasChildren ? (e) => { e.preventDefault(); setOpen(!open) } : undefined}
        aria-current={item.active ? 'page' : undefined}
        title={collapsed ? item.label : undefined}
      >
        {item.icon && (
          <span className="flex-shrink-0 h-4 w-4 flex items-center justify-center">
            {item.icon}
          </span>
        )}
        {!collapsed && (
          <>
            <span className="flex-1 truncate">{item.label}</span>
            {item.badge !== undefined && (
              <span className="ml-auto flex h-4 min-w-4 items-center justify-center rounded-full bg-primary/15 px-1 text-[10px] font-medium text-primary">
                {item.badge}
              </span>
            )}
          </>
        )}
      </a>
      {hasChildren && open && !collapsed && (
        <ul className="mt-0.5 space-y-0.5">
          {item.children!.map((child) => (
            <NavItem key={child.id} item={child} collapsed={collapsed} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  )
}

export function Sidebar({
  items = [],
  header,
  footer,
  collapsed = false,
  onCollapseToggle,
  className,
  children,
}: SidebarProps) {
  return (
    <div className={cn('flex h-full flex-col overflow-hidden', className)}>
      {/* Header slot */}
      {header && (
        <div className={cn('flex-shrink-0 border-b border-border p-3', collapsed && 'px-1.5')}>
          {header}
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-2" aria-label="Main navigation">
        {children ?? (
          <ul className="space-y-0.5">
            {items.map((item) => (
              <NavItem key={item.id} item={item} collapsed={collapsed} />
            ))}
          </ul>
        )}
      </nav>

      {/* Footer + collapse toggle */}
      <div className="flex-shrink-0 border-t border-border p-2">
        {footer && <div className="mb-2">{footer}</div>}
        {onCollapseToggle && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onCollapseToggle}
            className={cn('w-full justify-center', !collapsed && 'justify-between')}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {!collapsed && <span className="text-xs text-muted-foreground">Collapse</span>}
            <ChevronLeft
              className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')}
            />
          </Button>
        )}
      </div>
    </div>
  )
}
