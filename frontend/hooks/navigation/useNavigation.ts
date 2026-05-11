'use client'

import { usePathname, useRouter } from 'next/navigation'
import { useCallback } from 'react'
import { NAV_ROUTES, getActiveRoute, type NavRoute } from '@/lib/navigation/routes'
import { isRouteActive } from '@/lib/navigation/utils'
import { useCommandStore } from '@/stores/command.store'

export interface UseNavigationReturn {
  pathname: string
  activeRoute: NavRoute | undefined
  navRoutes: NavRoute[]
  isActive: (href: string) => boolean
  navigate: (href: string) => void
  navigateBack: () => void
}

/**
 * Primary navigation hook.
 * Provides pathname, active route, and type-safe navigation utilities.
 */
export function useNavigation(): UseNavigationReturn {
  const pathname = usePathname()
  const router = useRouter()
  const addRecentEntity = useCommandStore((s) => s.addRecentEntity)

  const activeRoute = getActiveRoute(pathname)

  const isActive = useCallback(
    (href: string) => isRouteActive(pathname, href),
    [pathname]
  )

  const navigate = useCallback(
    (href: string) => {
      router.push(href)
    },
    [router]
  )

  const navigateBack = useCallback(() => {
    router.back()
  }, [router])

  return {
    pathname,
    activeRoute,
    navRoutes: NAV_ROUTES,
    isActive,
    navigate,
    navigateBack,
  }
}
