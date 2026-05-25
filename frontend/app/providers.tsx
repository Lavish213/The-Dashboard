'use client'

import { NuqsAdapter } from 'nuqs/adapters/next/app'
import { ThemeProvider } from '@/providers/ThemeProvider'
import { QueryProvider } from '@/providers/QueryProvider'
import { AuthProvider } from '@/providers/AuthProvider'
import { ToastProvider } from '@/providers/ToastProvider'
import { RealtimeProvider } from '@/providers/RealtimeProvider'
import { WebsocketProvider } from '@/providers/WebsocketProvider'
import { AppShellRuntime } from '@/components/workspace/AppShellRuntime'

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <NuqsAdapter>
      <ThemeProvider>
        <QueryProvider>
          <AuthProvider>
            <WebsocketProvider>
              <RealtimeProvider>
                <ToastProvider>
                  <AppShellRuntime>{children}</AppShellRuntime>
                </ToastProvider>
              </RealtimeProvider>
            </WebsocketProvider>
          </AuthProvider>
        </QueryProvider>
      </ThemeProvider>
    </NuqsAdapter>
  )
}