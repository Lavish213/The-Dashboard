'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useCommandStore } from '@/stores/command.store'
import { CommandPalette } from '@/components/layout/CommandPalette'
import { useNavigation } from '@/hooks/navigation/useNavigation'
import { NAV_ROUTES } from '@/lib/navigation/routes'
import type { CommandGroup } from '@/components/layout/CommandPalette'
import {
  LayoutDashboard,
  Users,
  Phone,
  GitBranch,
  CheckSquare,
  Radio,
  FileText,
  BarChart2,
  Activity,
  Shield,
  Settings,
  RefreshCw,
} from 'lucide-react'

export function CommandPaletteProvider() {
  const open = useCommandStore((s) => s.open)
  const setOpen = useCommandStore((s) => s.setOpen)
  const { navigate } = useNavigation()
  const router = useRouter()

  const groups: CommandGroup[] = [
    {
      id: 'navigate',
      heading: 'Navigate',
      items: NAV_ROUTES.map((route) => {
        const Icon = route.icon
        return {
          id: route.id,
          label: route.label,
          icon: <Icon className="h-4 w-4" />,
          onSelect: () => navigate(route.href),
          keywords: [route.group, route.href],
        }
      }),
    },
    {
      id: 'actions',
      heading: 'Actions',
      items: [
        {
          id: 'goto-dashboard',
          label: 'Go to Dashboard',
          icon: <LayoutDashboard className="h-4 w-4" />,
          onSelect: () => { router.push('/dashboard'); setOpen(false) },
          keywords: ['home', 'overview', 'dashboard'],
        },
        {
          id: 'goto-leads',
          label: 'View Lead Pipeline',
          icon: <Users className="h-4 w-4" />,
          onSelect: () => { router.push('/leads'); setOpen(false) },
          keywords: ['leads', 'pipeline', 'kanban'],
        },
        {
          id: 'goto-calls',
          label: 'View Call History',
          icon: <Phone className="h-4 w-4" />,
          onSelect: () => { router.push('/calls'); setOpen(false) },
          keywords: ['calls', 'history', 'phone'],
        },
        {
          id: 'goto-sophia',
          label: 'Sophia Live Monitor',
          icon: <Radio className="h-4 w-4" />,
          onSelect: () => { router.push('/realtime'); setOpen(false) },
          keywords: ['sophia', 'live', 'realtime', 'monitor'],
        },
        {
          id: 'goto-approvals',
          label: 'Review Approvals',
          icon: <CheckSquare className="h-4 w-4" />,
          onSelect: () => { router.push('/approvals'); setOpen(false) },
          keywords: ['approvals', 'review', 'pending'],
        },
        {
          id: 'goto-workflows',
          label: 'View Workflows',
          icon: <GitBranch className="h-4 w-4" />,
          onSelect: () => { router.push('/workflows'); setOpen(false) },
          keywords: ['workflows', 'execution'],
        },
        {
          id: 'goto-transcripts',
          label: 'View Transcripts',
          icon: <FileText className="h-4 w-4" />,
          onSelect: () => { router.push('/transcripts'); setOpen(false) },
          keywords: ['transcripts', 'calls', 'chunks'],
        },
        {
          id: 'goto-analytics',
          label: 'View Analytics',
          icon: <BarChart2 className="h-4 w-4" />,
          onSelect: () => { router.push('/analytics'); setOpen(false) },
          keywords: ['analytics', 'metrics', 'funnel'],
        },
        {
          id: 'goto-activity',
          label: 'View Activity Feed',
          icon: <Activity className="h-4 w-4" />,
          onSelect: () => { router.push('/activity'); setOpen(false) },
          keywords: ['activity', 'events', 'feed'],
        },
        {
          id: 'goto-audit',
          label: 'View Audit Log',
          icon: <Shield className="h-4 w-4" />,
          onSelect: () => { router.push('/audit'); setOpen(false) },
          keywords: ['audit', 'log', 'history'],
        },
        {
          id: 'goto-settings',
          label: 'Open Settings',
          icon: <Settings className="h-4 w-4" />,
          onSelect: () => { router.push('/settings'); setOpen(false) },
          keywords: ['settings', 'config', 'sophia'],
        },
        {
          id: 'refresh',
          label: 'Refresh page',
          icon: <RefreshCw className="h-4 w-4" />,
          onSelect: () => { router.refresh(); setOpen(false) },
          keywords: ['refresh', 'reload'],
        },
      ],
    },
  ]

  return (
    <CommandPalette
      groups={groups}
      open={open}
      onOpenChange={setOpen}
      placeholder="Search pages and actions…"
    />
  )
}