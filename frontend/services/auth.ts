import { apiFetch } from '@/services/api'
import { useAuthStore } from '@/stores/auth.store'
import type { AuthUser } from '@/stores/auth.store'
import env from '@/config/environment'

const API_BASE = env.apiUrl

interface LoginPayload {
  email: string
  password: string
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: {
    id: string
    email: string
    full_name: string | null
    role: string
  }
}

interface MeResponse {
  id: string
  email: string
  full_name: string | null
  role: string
}

export async function login(payload: LoginPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(15_000),
    redirect: 'error',
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `Login failed (${res.status})`)
  }

  const data: LoginResponse = await res.json()

  const user: AuthUser = {
    id: data.user.id,
    email: data.user.email,
    name: data.user.full_name ?? data.user.email,
    role: data.user.role,
  }

  useAuthStore.getState().setUser(user, data.access_token, data.refresh_token)
}

export async function logout(): Promise<void> {
  try {
    await apiFetch('/api/v1/auth/logout', { method: 'POST' })
  } catch {
  } finally {
    useAuthStore.getState().clearUser()
  }
}

export async function getMe(): Promise<AuthUser> {
  const data = await apiFetch<MeResponse>('/api/v1/auth/me')
  return {
    id: data.id,
    email: data.email,
    name: data.full_name ?? data.email,
    role: data.role,
  }
}
