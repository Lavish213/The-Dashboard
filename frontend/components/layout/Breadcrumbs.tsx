import * as React from 'react'
import { cn } from '@/lib/utils'
import { ChevronRight } from 'lucide-react'

export interface BreadcrumbItem {
  label: string
  href?: string
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[]
  className?: string
}

export function Breadcrumbs({ items, className }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb" className={cn('flex items-center', className)}>
      <ol className="flex items-center gap-1 text-xs text-muted-foreground">
        {items.map((item, idx) => {
          const isLast = idx === items.length - 1
          return (
            <li key={idx} className="flex items-center gap-1">
              {idx > 0 && <ChevronRight className="h-3 w-3 opacity-40" aria-hidden="true" />}
              {isLast || !item.href ? (
                <span
                  className={cn(
                    isLast ? 'font-medium text-foreground' : 'text-muted-foreground'
                  )}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {item.label}
                </span>
              ) : (
                <a
                  href={item.href}
                  className="hover:text-foreground transition-colors"
                >
                  {item.label}
                </a>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
