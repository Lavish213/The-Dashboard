import { create } from 'zustand'

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

export interface AuthUser {
  id: string
  email: string
  name: string
  role: string
  avatarUrl?: string
}

interface AuthState {
  status: AuthStatus
  user: AuthUser | null
  token: string | null
  refreshToken: string | null
  setUser: (user: AuthUser, token: string, refreshToken: string) => void
  clearUser: () => void
  setStatus: (status: AuthStatus) => void
}

export const useAuthStore = create<AuthState>()((set) => ({
  status: 'unauthenticated',
  user: null,
  token: null,
  refreshToken: null,

  setUser: (user, token, refreshToken) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('karpathys_token', token)
      localStorage.setItem('karpathys_refresh_token', refreshToken)
      localStorage.setItem('karpathys_user', JSON.stringify(user))
    }
    set({ user, token, refreshToken, status: 'authenticated' })
  },

  clearUser: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('karpathys_token')
      localStorage.removeItem('karpathys_refresh_token')
      localStorage.removeItem('karpathys_user')
    }
    set({ user: null, token: null, refreshToken: null, status: 'unauthenticated' })
  },

  setStatus: (status) => set({ status }),
}))