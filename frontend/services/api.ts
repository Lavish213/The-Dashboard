import env from '@/config/environment'
import { useAuthStore } from '@/stores/auth.store'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

function responseError(status: number, body: string): string {
  try {
    const value: unknown = JSON.parse(body)
    if (value && typeof value === 'object' && 'detail' in value) {
      if (typeof value.detail === 'string' && value.detail.trim()) return value.detail.slice(0, 1000)
      if (Array.isArray(value.detail)) {
        const messages = value.detail.map((item: unknown) => item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string' ? item.msg : '').filter(Boolean).slice(0, 3)
        if (messages.length) return messages.join('; ').slice(0, 1000)
      }
    }
  } catch {}
  return `Request failed (${status})`
}

let _isRefreshing = false
let _refreshQueue: Array<(token: string | null) => void> = []

function _notifyQueue(token: string | null) {
  _refreshQueue.forEach((resolve) => resolve(token))
  _refreshQueue = []
}

async function _attemptRefresh(): Promise<string | null> {
  const refreshToken = typeof window !== 'undefined'
    ? localStorage.getItem('karpathys_refresh_token')
    : null

  if (!refreshToken) {
    useAuthStore.getState().clearUser()
    if (typeof window !== 'undefined') window.location.replace('/login')
    return null
  }

  try {
    const res = await fetch(`${env.apiUrl}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
      signal: AbortSignal.timeout(15_000),
      redirect: 'error',
    })

    if (!res.ok) {
      useAuthStore.getState().clearUser()
      if (typeof window !== 'undefined') window.location.replace('/login')
      return null
    }

    const data = await res.json()
    const { user, setUser } = useAuthStore.getState()
    if (user) {
      setUser(user, data.access_token, data.refresh_token)
    }
    return data.access_token as string
  } catch {
    useAuthStore.getState().clearUser()
    if (typeof window !== 'undefined') window.location.replace('/login')
    return null
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\')) {
    throw new ApiError(400, 'API paths must be relative to the configured service')
  }
  const token = typeof window !== 'undefined'
    ? localStorage.getItem('karpathys_token')
    : null

  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')

  if (token) headers.set('Authorization', `Bearer ${token}`)

  const url = `${env.apiUrl}${path}`
  const request = { ...init, headers, redirect: 'error' as const, signal: init.signal
    ? AbortSignal.any([init.signal, AbortSignal.timeout(20_000)])
    : AbortSignal.timeout(20_000) }
  let res = await fetch(url, request)

  if (res.status === 401) {
    let newToken: string | null = null

    if (_isRefreshing) {
      newToken = await new Promise<string | null>((resolve) => {
        _refreshQueue.push(resolve)
      })
    } else {
      _isRefreshing = true
      try {
        newToken = await _attemptRefresh()
      } finally {
        _notifyQueue(newToken)
        _isRefreshing = false
      }
    }

    if (newToken) {
      headers.set('Authorization', `Bearer ${newToken}`)
      res = await fetch(url, request)
    } else {
      throw new ApiError(401, 'Session expired')
    }
  }

  if (!res.ok) {
    const body = await res.text()
    throw new ApiError(res.status, responseError(res.status, body))
  }

  const text = await res.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}
