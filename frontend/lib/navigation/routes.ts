import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  Users,
  Building2,
  Phone,
  GitBranch,
  CheckSquare,
  Activity,
  BarChart2,
  Radio,
  ScrollText,
  Settings,
  PhoneCall,
} from 'lucide-react'

export interface NavRoute {
  id: string
  label: string
  href: string
  icon: LucideIcon
  group: NavGroup
  /** Badge count source key — populated by stores in Phase 3+ */
  badgeKey?: string
  /** Sub-routes (detail pages) — not shown in nav but used for active matching */
  matchPrefixes?: string[]
}

export type NavGroup = 'operations' | 'governance' | 'insights' | 'system'

export const NAV_GROUPS: { id: NavGroup; label: string }[] = [
  { id: 'operations', label: 'Operations' },
  { id: 'governance', label: 'Governance' },
  { id: 'insights', label: 'Insights' },
  { id: 'system', label: 'System' },
]

export const NAV_ROUTES: NavRoute[] = [
  // Operations
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    group: 'operations',
  },
  {
    id: 'leads',
    label: 'Leads',
    href: '/leads',
    icon: Users,
    group: 'operations',
    matchPrefixes: ['/leads/'],
  },
  {
    id: 'properties',
    label: 'Properties',
    href: '/properties',
    icon: Building2,
    group: 'operations',
    matchPrefixes: ['/properties/'],
  },
  {
    id: 'calls',
    label: 'Calls',
    href: '/calls',
    icon: Phone,
    group: 'operations',
    matchPrefixes: ['/calls/'],
  },
  {
    id: 'workflows',
    label: 'Workflows',
    href: '/workflows',
    icon: GitBranch,
    group: 'operations',
    matchPrefixes: ['/workflows/'],
  },
  // Governance
  {
    id: 'approvals',
    label: 'Approvals',
    href: '/approvals',
    icon: CheckSquare,
    group: 'governance',
    badgeKey: 'approvalsPending',
  },
  {
    id: 'realtime',
    label: 'Realtime',
    href: '/realtime',
    icon: Radio,
    group: 'governance',
  },
  {
    id: 'audit',
    label: 'Audit Log',
    href: '/audit',
    icon: ScrollText,
    group: 'governance',
  },
  // Insights
  {
    id: 'analytics',
    label: 'Analytics',
    href: '/analytics',
    icon: BarChart2,
    group: 'insights',
  },
  {
    id: 'activity',
    label: 'Activity',
    href: '/activity',
    icon: Activity,
    group: 'insights',
  },
  {
    id: 'transcripts',
    label: 'Transcripts',
    href: '/transcripts',
    icon: PhoneCall,
    group: 'insights',
    matchPrefixes: ['/transcripts/'],
  },
  // System
  {
    id: 'settings',
    label: 'Settings',
    href: '/settings',
    icon: Settings,
    group: 'system',
  },
]

/** Routes that render WITHOUT the app shell (no sidebar/topbar) */
export const AUTH_ROUTES: string[] = ['/login', '/register', '/forgot-password', '/reset-password']

/** Routes accessible without authentication (Phase 3 will enforce) */
export const PUBLIC_ROUTES: string[] = ['/login', '/register', '/forgot-password', '/reset-password']

export function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTES.some((r) => pathname === r || pathname.startsWith(r + '/'))
}

export function getRouteById(id: string): NavRoute | undefined {
  return NAV_ROUTES.find((r) => r.id === id)
}

/** Returns the nav route that best matches the current pathname */
export function getActiveRoute(pathname: string): NavRoute | undefined {
  // Exact match first
  const exact = NAV_ROUTES.find((r) => r.href === pathname)
  if (exact) return exact

  // Prefix match (for detail pages)
  return NAV_ROUTES.find(
    (r) =>
      r.matchPrefixes?.some((prefix) => pathname.startsWith(prefix)) ||
      (r.href !== '/' && pathname.startsWith(r.href + '/'))
  )
}
