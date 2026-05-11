'use client'

import { useWebSocketContext } from '@/providers/WebsocketProvider'
import { useWebSocketStore } from '@/stores/websocket.store'
import type { ClientMessage } from '@/types/websocket'

export function useWebsocket() {
  const { send } = useWebSocketContext()
  const status = useWebSocketStore((s) => s.status)
  const connectionId = useWebSocketStore((s) => s.connectionId)
  const lastError = useWebSocketStore((s) => s.lastError)

  return {
    status,
    connected: status === 'connected',
    connectionId,
    lastError,
    send: (msg: ClientMessage) => send(msg),
  }
}
