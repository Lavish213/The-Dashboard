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
  const token = typeof window !== 'undefined'
    ? localStorage.getItem('karpathys_token')
    : null

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> ?? {}),
  }

  if (token) headers['Authorization'] = `Bearer ${token}`

  const url = path.startsWith('http') ? path : `${env.apiUrl}${path}`
  let res = await fetch(url, { ...init, headers })

  if (res.status === 401) {
    let newToken: string | null = null

    if (_isRefreshing) {
      newToken = await new Promise<string | null>((resolve) => {
        _refreshQueue.push(resolve)
      })
    } else {
      _isRefreshing = true
      newToken = await _attemptRefresh()
      _notifyQueue(newToken)
      _isRefreshing = false
    }

    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`
      res = await fetch(url, { ...init, headers })
    } else {
      throw new ApiError(401, 'Session expired')
    }
  }

  if (!res.ok) {
    const body = await res.text()
    throw new ApiError(res.status, body)
  }

  const text = await res.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}