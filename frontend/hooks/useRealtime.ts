'use client'

import { useEffect } from 'react'
import { useWebSocketContext } from '@/providers/WebsocketProvider'
import { useWebSocketStore } from '@/stores/websocket.store'
import type { Channel, RealtimeEvent } from '@/types/websocket'

/**
 * Subscribe to a realtime channel and invoke handler on each new event.
 * Automatically subscribes on mount and unsubscribes on unmount.
 */
export function useRealtime(channel: Channel, handler: (event: RealtimeEvent) => void) {
  const { send, registry } = useWebSocketContext()
  const status = useWebSocketStore((s) => s.status)

  useEffect(() => {
    if (status !== 'connected') return

    send({ type: 'subscribe', channel })
    const unregister = registry.register(channel, handler)

    return () => {
      unregister()
      send({ type: 'unsubscribe', channel })
    }
  }, [channel, status]) // eslint-disable-line react-hooks/exhaustive-deps
}
