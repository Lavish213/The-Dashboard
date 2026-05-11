'use client'

import React, { createContext, useContext, useEffect, useRef } from 'react'
import env from '@/config/environment'
import { buildWsUrl, WebSocketClient } from '@/lib/websocket/client'
import { MessageDispatcher } from '@/lib/realtime/dispatcher'
import { HandlerRegistry } from '@/lib/realtime/registry'
import { useAuthStore } from '@/stores/auth.store'
import { useRealtimeStore } from '@/stores/realtime.store'
import { useWebSocketStore } from '@/stores/websocket.store'
import type { ClientMessage } from '@/types/websocket'

interface WebSocketContextValue {
  send: (msg: ClientMessage) => void
  registry: HandlerRegistry
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null)

export function WebsocketProvider({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  const { setStatus, setConnectionId, setLastError } = useWebSocketStore()
  const { addChannel, removeChannel, recordEvent, reset } = useRealtimeStore()

  const clientRef = useRef<WebSocketClient | null>(null)
  const dispatcherRef = useRef<MessageDispatcher | null>(null)

  // Initialise dispatcher once
  if (!dispatcherRef.current) {
    dispatcherRef.current = new MessageDispatcher({
      onConnected: (connectionId) => {
        setConnectionId(connectionId)
        setLastError(null)
      },
      onDisconnected: () => {
        reset()
        setConnectionId(null)
      },
      onSubscribed: addChannel,
      onUnsubscribed: removeChannel,
      onError: (code, message) => setLastError(`${code}: ${message}`),
    })
  }

  useEffect(() => {
    if (!token) return

    const url = buildWsUrl(env.wsUrl, token)
    const dispatcher = dispatcherRef.current!

    const client = new WebSocketClient(url, {
      onStatusChange: (status) => {
        setStatus(status)
        if (status === 'reconnecting') {
          dispatcher.reset()
          reset()
        }
      },
      onMessage: (msg) => {
        if (msg.type === 'event') recordEvent()
        dispatcher.dispatch(msg)
      },
    })

    clientRef.current = client
    client.connect()

    return () => {
      client.disconnect()
      clientRef.current = null
    }
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  const value: WebSocketContextValue = {
    send: (msg) => clientRef.current?.send(msg),
    registry: dispatcherRef.current.registry,
  }

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocketContext(): WebSocketContextValue {
  const ctx = useContext(WebSocketContext)
  if (!ctx) throw new Error('useWebSocketContext must be used within WebsocketProvider')
  return ctx
}
