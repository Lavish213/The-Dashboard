'use client'

import { Toaster } from 'sonner'
import { useTheme } from '@/hooks/ui/useTheme'

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const { isDark } = useTheme()
  return (
    <>
      {children}
      <Toaster
        position="bottom-right"
        theme={isDark ? 'dark' : 'light'}
        richColors
        closeButton
        toastOptions={{
          duration: 4000,
          classNames: { error: '!text-destructive !bg-card !border-destructive/30' },
        }}
      />
    </>
  )
}
