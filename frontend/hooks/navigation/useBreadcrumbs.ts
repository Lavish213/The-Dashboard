'use client'

import { usePathname } from 'next/navigation'
import { useMemo } from 'react'
import { computeBreadcrumbs, type BreadcrumbSegment } from '@/lib/navigation/utils'

export type { BreadcrumbSegment }

/**
 * Computes breadcrumb trail from the current pathname.
 * Detail-level labels are generic in Phase 2; enriched with real entity names in Phase 3+.
 */
export function useBreadcrumbs(): BreadcrumbSegment[] {
  const pathname = usePathname()
  return useMemo(() => computeBreadcrumbs(pathname), [pathname])
}
