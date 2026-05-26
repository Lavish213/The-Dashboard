import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  BarChart2,
  Bell,
  Building2,
  CalendarDays,
  CheckSquare,
  GitBranch,
  Handshake,
  LayoutDashboard,
  Phone,
  PhoneCall,
  Radio,
  ScrollText,
  Settings,
  Share2,
  Users,
} from 'lucide-react'

export interface NavRoute {
  id: string
  label: string
  href: string
  icon: LucideIcon
  group: NavGroup
  badgeKey?: string
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
    id: 'deals',
    label: 'Deals',
    href: '/deals',
    icon: Handshake,
    group: 'operations',
    matchPrefixes: ['/deals/'],
  },
  {
    id: 'followups',
    label: 'Follow-ups',
    href: '/followups',
    icon: Bell,
    group: 'operations',
  },
  {
    id: 'calendar',
    label: 'Calendar',
    href: '/calendar',
    icon: CalendarDays,
    group: 'operations',
  },
  {
    id: 'social',
    label: 'Social',
    href: '/social',
    icon: Share2,
    group: 'operations',
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
    label: 'Sophia Live',
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
  {
    id: 'settings',
    label: 'Settings',
    href: '/settings',
    icon: Settings,
    group: 'system',
  },
]

export const AUTH_ROUTES: string[] = ['/login', '/register', '/forgot-password', '/reset-password']

export const PUBLIC_ROUTES: string[] = ['/login', '/register', '/forgot-password', '/reset-password']

export function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTES.some((r) => pathname === r || pathname.startsWith(r + '/'))
}

export function getRouteById(id: string): NavRoute | undefined {
  return NAV_ROUTES.find((r) => r.id === id)
}

export function getActiveRoute(pathname: string): NavRoute | undefined {
  const exact = NAV_ROUTES.find((r) => r.href === pathname)
  if (exact) return exact
  return NAV_ROUTES.find(
    (r) =>
      r.matchPrefixes?.some((prefix) => pathname.startsWith(prefix)) ||
      (r.href !== '/' && pathname.startsWith(r.href + '/'))
  )
}