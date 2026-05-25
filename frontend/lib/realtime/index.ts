import { useAuthStore } from '@/stores/auth.store'
import { useEffect, useRef, useState } from 'react'

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? ''

const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 30000
const RECONNECT_JITTER = 0.1
const NON_RECOVERABLE_CODES = new Set([4001, 4000])

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

type MessageHandler = (payload: unknown) => void

interface RealtimeClientOptions {
  onStatusChange?: (status: ConnectionStatus) => void
}

class RealtimeClient {
  private _ws: WebSocket | null = null
  private _connectionId: string | null = null
  private _status: ConnectionStatus = 'disconnected'
  private _shouldReconnect = false
  private _reconnectAttempts = 0
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private _subscriptions: Set<string> = new Set()
  private _handlers: Map<string, Set<MessageHandler>> = new Map()
  private _onStatusChange: ((status: ConnectionStatus) => void) | null = null

  constructor(options: RealtimeClientOptions = {}) {
    this._onStatusChange = options.onStatusChange ?? null
  }

  private _setStatus(status: ConnectionStatus) {
    this._status = status
    this._onStatusChange?.(status)
  }

  private _backoffMs(): number {
    const base = Math.min(
      RECONNECT_BASE_MS * Math.pow(2, this._reconnectAttempts),
      RECONNECT_MAX_MS,
    )
    const jitter = base * RECONNECT_JITTER * (Math.random() * 2 - 1)
    return Math.floor(base + jitter)
  }

  private _scheduleReconnect() {
    if (!this._shouldReconnect) return
    const delay = this._backoffMs()
    this._reconnectAttempts += 1
    this._reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  private _clearReconnectTimer() {
    if (this._reconnectTimer !== null) {
      clearTimeout(this._reconnectTimer)
      this._reconnectTimer = null
    }
  }

  private _dispatch(eventType: string, payload: unknown) {
    const handlers = this._handlers.get(eventType)
    if (handlers) {
      handlers.forEach((h) => h(payload))
    }
    // also dispatch to wildcard handlers
    const wildcards = this._handlers.get('*')
    if (wildcards) {
      wildcards.forEach((h) => h({ type: eventType, payload }))
    }
  }

  private _handleMessage(raw: string) {
    let msg: Record<string, unknown>
    try {
      msg = JSON.parse(raw)
    } catch {
      return
    }

    const type = msg.type as string | undefined
    if (!type) return

    switch (type) {
      case 'ping':
        this._send({ type: 'pong' })
        break

      case 'connected_ack':
        this._connectionId = msg.connection_id as string
        this._setStatus('connected')
        this._reconnectAttempts = 0
        // re-subscribe to all channels after reconnect
        this._subscriptions.forEach((channel) => {
          this._send({ type: 'subscribe', channel })
        })
        break

      case 'subscribed_ack':
      case 'unsubscribed_ack':
        this._dispatch(type, msg)
        break

      case 'event':
        this._dispatch(msg.event_type as string, msg.payload)
        this._dispatch('event', msg)
        break

      case 'authentication_error':
        this._setStatus('error')
        this._shouldReconnect = false
        this._dispatch('auth_error', msg)
        break

      case 'error':
        this._dispatch('error', msg)
        break

      default:
        this._dispatch(type, msg)
    }
  }

  private _send(data: unknown): boolean {
    if (this._ws?.readyState !== WebSocket.OPEN) return false
    try {
      this._ws.send(JSON.stringify(data))
      return true
    } catch {
      return false
    }
  }

  connect() {
    if (
      this._ws?.readyState === WebSocket.OPEN ||
      this._ws?.readyState === WebSocket.CONNECTING
    ) {
      return
    }

    const { token } = useAuthStore.getState()
    if (!token) {
      this._setStatus('error')
      return
    }

    this._clearReconnectTimer()
    this._setStatus('connecting')
    this._shouldReconnect = true

    const url = `${WS_BASE}/api/v1/realtime/ws?token=${encodeURIComponent(token)}`

    try {
      this._ws = new WebSocket(url)
    } catch {
      this._setStatus('error')
      this._scheduleReconnect()
      return
    }

    this._ws.onopen = () => {
      // status set to connected after connected_ack received
    }

    this._ws.onmessage = (event) => {
      this._handleMessage(event.data as string)
    }

    this._ws.onclose = (event) => {
      this._ws = null
      this._connectionId = null

      if (NON_RECOVERABLE_CODES.has(event.code)) {
        this._shouldReconnect = false
        this._setStatus('error')
        return
      }

      this._setStatus('disconnected')
      this._scheduleReconnect()
    }

    this._ws.onerror = () => {
      // onerror always followed by onclose — let onclose handle reconnect
    }
  }

  disconnect() {
    this._shouldReconnect = false
    this._clearReconnectTimer()
    if (this._ws) {
      this._ws.close(1000, 'Client disconnected')
      this._ws = null
    }
    this._connectionId = null
    this._setStatus('disconnected')
  }

  subscribe(channel: string) {
    this._subscriptions.add(channel)
    this._send({ type: 'subscribe', channel })
  }

  unsubscribe(channel: string) {
    this._subscriptions.delete(channel)
    this._send({ type: 'unsubscribe', channel })
  }

  on(eventType: string, handler: MessageHandler) {
    if (!this._handlers.has(eventType)) {
      this._handlers.set(eventType, new Set())
    }
    this._handlers.get(eventType)!.add(handler)
  }

  off(eventType: string, handler: MessageHandler) {
    this._handlers.get(eventType)?.delete(handler)
  }

  get status(): ConnectionStatus {
    return this._status
  }

  get connectionId(): string | null {
    return this._connectionId
  }
}

export const realtimeClient = new RealtimeClient()

// --- React hook ---

export function useRealtime(channels: string[] = []) {
  const [status, setStatus] = useState<ConnectionStatus>(realtimeClient.status)
  const channelsRef = useRef<string[]>(channels)

  useEffect(() => {
    channelsRef.current = channels
  }, [channels])

  useEffect(() => {
    const client = new RealtimeClient({
      onStatusChange: (s) => setStatus(s),
    })

    client.connect()

    const timer = setTimeout(() => {
      channelsRef.current.forEach((ch) => client.subscribe(ch))
    }, 100)

    return () => {
      clearTimeout(timer)
      client.disconnect()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { status, realtimeClient }
}

export type { ConnectionStatus, MessageHandler }