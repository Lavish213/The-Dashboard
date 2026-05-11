'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetBody, SheetContent } from '@/components/ui/sheet'
import type { SidebarNavItem } from './Sidebar'

interface MobileNavProps {
  items?: SidebarNavItem[]
  header?: React.ReactNode
  children?: React.ReactNode
  className?: string
}

export function MobileNav({
  items = [],
  header,
  children,
  className,
}: MobileNavProps) {
  const [open, setOpen] = React.useState(false)

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen(true)}
        className={cn('h-8 w-8 p-0 md:hidden', className)}
        aria-label="Open navigation menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" className="w-72 p-0">
          {header && (
            <div className="border-b border-border p-4">{header}</div>
          )}
          <SheetBody>
            <nav aria-label="Mobile navigation">
              {children ?? (
                <ul className="space-y-0.5 p-2">
                  {items.map((item) => (
                    <li key={item.id}>
                      <a
                        href={item.href ?? '#'}
                        className={cn(
                          'flex items-center gap-2.5 rounded-md px-2 py-2 text-sm transition-colors',
                          'text-muted-foreground hover:bg-muted hover:text-foreground',
                          item.active && 'bg-primary/10 text-primary font-medium'
                        )}
                        onClick={() => setOpen(false)}
                        aria-current={item.active ? 'page' : undefined}
                      >
                        {item.icon && (
                          <span className="h-4 w-4 flex items-center justify-center">
                            {item.icon}
                          </span>
                        )}
                        <span className="flex-1">{item.label}</span>
                        {item.badge !== undefined && (
                          <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary/15 px-1 text-[10px] font-medium text-primary">
                            {item.badge}
                          </span>
                        )}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </nav>
          </SheetBody>
        </SheetContent>
      </Sheet>
    </>
  )
}
