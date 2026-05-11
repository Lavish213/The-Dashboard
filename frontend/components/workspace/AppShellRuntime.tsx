'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { AppNav } from '@/components/navigation/AppNav'
import { BottomNav } from '@/components/navigation/BottomNav'
import { SkipNav } from '@/components/navigation/SkipNav'
import { CommandPaletteProvider } from '@/components/navigation/CommandPaletteProvider'
import { Topbar } from '@/components/layout/Topbar'
import { Breadcrumbs } from '@/components/layout/Breadcrumbs'
import { useSidebar } from '@/hooks/layout/useSidebar'
import { useFocusRestore } from '@/hooks/layout/useFocusRestore'
import { useBreadcrumbs } from '@/hooks/navigation/useBreadcrumbs'
import { isAuthRoute } from '@/lib/navigation/routes'
import { MobileNav } from '@/components/layout/MobileNav'
import { NAV_ROUTES } from '@/lib/navigation/routes'
import { useNavigation } from '@/hooks/navigation/useNavigation'
import { Bell, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCommandStore } from '@/stores/command.store'

interface AppShellRuntimeProps {
  children: React.ReactNode
}

/** Inner authenticated shell — only rendered for non-auth routes */
function AuthenticatedShell({ children }: { children: React.ReactNode }) {
  const { collapsed, toggle } = useSidebar()
  const breadcrumbs = useBreadcrumbs()
  const mainRef = useFocusRestore()
  const openCommand = useCommandStore((s) => s.setOpen)
  const { isActive } = useNavigation()

  const sidebarWidth = collapsed ? 56 : 280

  const navItems = NAV_ROUTES.map((r) => ({
    id: r.id,
    label: r.label,
    href: r.href,
    icon: <r.icon className="h-4 w-4" />,
    active: isActive(r.href),
  }))

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <SkipNav />

      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden md:flex flex-col flex-shrink-0 border-r border-border overflow-hidden',
          'transition-[width] duration-200'
        )}
        style={{ width: sidebarWidth }}
        aria-label="Sidebar"
      >
        <AppNav collapsed={collapsed} onCollapseToggle={toggle} />
      </aside>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header
          className="flex-shrink-0 border-b border-border"
          style={{ height: 48 }}
          role="banner"
        >
          <Topbar
            left={
              <div className="flex items-center gap-3">
                {/* Mobile hamburger */}
                <MobileNav items={navItems} />
                {breadcrumbs.length > 0 && (
                  <Breadcrumbs items={breadcrumbs} className="hidden sm:flex" />
                )}
              </div>
            }
            right={
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openCommand(true)}
                  className="h-8 gap-2 px-2 text-xs text-muted-foreground hidden sm:flex"
                  aria-label="Open command palette"
                >
                  <Search className="h-3.5 w-3.5" />
                  <span>Search</span>
                  <kbd className="text-[10px] opacity-60">⌘K</kbd>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openCommand(true)}
                  className="h-8 w-8 p-0 sm:hidden"
                  aria-label="Search"
                >
                  <Search className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  aria-label="Notifications"
                >
                  <Bell className="h-4 w-4" />
                </Button>
              </div>
            }
            showThemeToggle
          />
        </header>

        {/* Main content area */}
        <main
          id="main-content"
          ref={mainRef as React.RefObject<HTMLElement>}
          className="flex-1 overflow-auto focus:outline-none"
          role="main"
          tabIndex={-1}
          aria-label="Main content"
        >
          {children}
        </main>
      </div>

      {/* Mobile bottom nav */}
      <BottomNav />

      {/* Global command palette */}
      <CommandPaletteProvider />
    </div>
  )
}

/**
 * AppShellRuntime — top-level shell orchestrator.
 * Reads pathname to decide whether to render the authenticated shell
 * (with sidebar/topbar) or the auth layout (centered, no chrome).
 *
 * Auth route detection: Phase 3 will add JWT validation here.
 */
export function AppShellRuntime({ children }: AppShellRuntimeProps) {
  const pathname = usePathname()

  if (isAuthRoute(pathname)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        {children}
      </div>
    )
  }

  return <AuthenticatedShell>{children}</AuthenticatedShell>
}
