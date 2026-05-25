'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/stores/auth.store'
import { getMe } from '@/services/auth'
import env from '@/config/environment'

const PUBLIC_PATHS = ['/login', '/register', '/forgot-password', '/reset-password']

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'))
}

async function tryRefresh(refreshToken: string): Promise<string | null> {
  try {
    const res = await fetch(`${env.apiUrl}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return null
    const data = await res.json()
    localStorage.setItem('karpathys_token', data.access_token)
    localStorage.setItem('karpathys_refresh_token', data.refresh_token)
    return data.access_token as string
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { setUser, clearUser, setStatus } = useAuthStore()
  const router = useRouter()
  const pathname = usePathname()
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const hydrate = async () => {
      setStatus('loading')

      const token = localStorage.getItem('karpathys_token')
      const refreshToken = localStorage.getItem('karpathys_refresh_token')
      const userRaw = localStorage.getItem('karpathys_user')

      if (!token && !refreshToken) {
        clearUser()
        setHydrated(true)
        return
      }

      if (token) {
        try {
          const freshUser = await getMe()
          setUser(freshUser, token, refreshToken ?? '')
          setHydrated(true)
          return
        } catch {
          // access token failed — try refresh before giving up
        }
      }

      if (refreshToken) {
        const newToken = await tryRefresh(refreshToken)
        if (newToken) {
          try {
            const freshUser = await getMe()
            const parsedUser = userRaw ? JSON.parse(userRaw) : null
            setUser(freshUser, newToken, localStorage.getItem('karpathys_refresh_token') ?? '')
            setHydrated(true)
            return
          } catch {
            // refresh succeeded but /me failed — clear
          }
        }
      }

      clearUser()
      setHydrated(true)
    }

    hydrate()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!hydrated) return
    const { status } = useAuthStore.getState()
    if (status === 'unauthenticated' && !isPublicPath(pathname)) {
      router.replace('/login')
    }
  }, [hydrated, pathname, router])

  if (!hydrated) return null

  return <>{children}</>
}