import { NAV_ROUTES } from './routes'

export interface BreadcrumbSegment {
  label: string
  href?: string
}

/**
 * Compute breadcrumb trail from a pathname.
 * Handles both list routes (/leads) and detail routes (/leads/123).
 */
export function computeBreadcrumbs(pathname: string): BreadcrumbSegment[] {
  const segments: BreadcrumbSegment[] = []

  // Find the primary nav route
  const navRoute = NAV_ROUTES.find(
    (r) =>
      r.href === pathname ||
      r.matchPrefixes?.some((p) => pathname.startsWith(p)) ||
      (r.href !== '/' && pathname.startsWith(r.href + '/'))
  )

  if (!navRoute) return segments

  // Add the nav route as a breadcrumb
  if (pathname === navRoute.href) {
    segments.push({ label: navRoute.label })
  } else {
    segments.push({ label: navRoute.label, href: navRoute.href })
    // Add a generic detail label — real label resolved in Phase 3+ from server data
    segments.push({ label: 'Detail' })
  }

  return segments
}

/**
 * Normalizes a route path for display (removes leading slash, converts dashes to spaces).
 */
export function formatPathSegment(segment: string): string {
  return segment
    .replace(/^\//, '')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Returns true if `pathname` is active for the given `href`.
 * Considers exact match and prefix match for nested routes.
 */
export function isRouteActive(pathname: string, href: string): boolean {
  if (href === pathname) return true
  if (href !== '/dashboard' && pathname.startsWith(href + '/')) return true
  return false
}
