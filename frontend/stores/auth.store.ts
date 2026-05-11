import { create } from 'zustand'

/**
 * Auth store — Phase 2 shell.
 * Token management, session refresh, and RBAC enforcement added in Phase 3.
 */

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

  // Phase 3 will implement these properly
  setUser: (user: AuthUser, token: string) => void
  clearUser: () => void
  setStatus: (status: AuthStatus) => void
}

export const useAuthStore = create<AuthState>()((set) => ({
  status: 'unauthenticated',
  user: null,
  token: null,

  setUser: (user, token) => set({ user, token, status: 'authenticated' }),
  clearUser: () => set({ user: null, token: null, status: 'unauthenticated' }),
  setStatus: (status) => set({ status }),
}))
