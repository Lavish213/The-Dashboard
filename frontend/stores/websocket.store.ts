import { create } from 'zustand'
import type { ConnectionStatus } from '@/types/websocket'

interface WebSocketState {
  status: ConnectionStatus
  connectionId: string | null
  reconnectAttempts: number
  lastConnectedAt: number | null
  lastError: string | null

  setStatus: (status: ConnectionStatus) => void
  setConnectionId: (id: string | null) => void
  setReconnectAttempts: (n: number) => void
  setLastError: (err: string | null) => void
}

export const useWebSocketStore = create<WebSocketState>()((set) => ({
  status: 'disconnected',
  connectionId: null,
  reconnectAttempts: 0,
  lastConnectedAt: null,
  lastError: null,

  setStatus: (status) =>
    set((s) => ({
      status,
      lastConnectedAt: status === 'connected' ? Date.now() : s.lastConnectedAt,
    })),
  setConnectionId: (connectionId) => set({ connectionId }),
  setReconnectAttempts: (reconnectAttempts) => set({ reconnectAttempts }),
  setLastError: (lastError) => set({ lastError }),
}))
