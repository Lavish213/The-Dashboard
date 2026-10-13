/**
 * Native WebSocket client with:
 * - Single-use ticket auth
 * - Automatic reconnect with exponential backoff
 * - Heartbeat ping/pong
 * - Typed message dispatch via callbacks
 */
"use client";

import type { ClientMessage, ConnectionStatus, ServerMessage } from "@/types/websocket";
import { ReconnectStrategy } from "./reconnect";

export interface WebSocketClientCallbacks {
  onStatusChange: (status: ConnectionStatus) => void;
  onMessage: (msg: ServerMessage) => void;
  /** Called when reconnect succeeds (not the initial connect). */
  onReconnected?: () => void;
  /** Called each time a reconnect attempt is scheduled. n = total attempts so far. */
  onAttemptChange?: (n: number) => void;
}

const PONG_RESPONSE = JSON.stringify({ type: "pong" });

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnect: ReconnectStrategy;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private destroyed = false;
  private status: ConnectionStatus = "disconnected";

  constructor(
    private readonly url: string | (() => Promise<string>),
    private readonly callbacks: WebSocketClientCallbacks,
  ) {
    this.reconnect = new ReconnectStrategy();
  }

  connect(): void {
    if (this.destroyed) return;
    this._setStatus("connecting");
    this._openSocket();
  }

  disconnect(): void {
    this.destroyed = true;
    this._clearReconnectTimer();
    this.ws?.close(1000);
    this.ws = null;
    this._setStatus("disconnected");
  }

  send(msg: ClientMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private async _openSocket(): Promise<void> {
    let ws: WebSocket;
    try {
      const url = typeof this.url === 'function' ? await this.url() : this.url;
      if (this.destroyed) return;
      ws = new WebSocket(url);
    } catch {
      if (!this.destroyed) this._scheduleReconnect();
      return;
    }
    this.ws = ws;

    ws.onopen = () => {
      const wasReconnect = this.reconnect.attemptCount > 0;
      this.reconnect.reset();
      this._setStatus("connected");
      if (wasReconnect) {
        this.callbacks.onReconnected?.();
      }
    };

    ws.onmessage = (evt: MessageEvent<string>) => {
      let msg: ServerMessage;
      try {
        msg = JSON.parse(evt.data) as ServerMessage;
      } catch {
        return;
      }
      // Respond to ping immediately
      if (msg.type === "ping") {
        ws.send(PONG_RESPONSE);
      }
      this.callbacks.onMessage(msg);
    };

    ws.onclose = (evt) => {
      this.ws = null;
      if (this.destroyed) return;
      if (evt.code === 4001) {
        // Auth error — do not reconnect
        this._setStatus("error");
        return;
      }
      this._scheduleReconnect();
    };

    ws.onerror = () => {
      // onclose fires after onerror — let it handle reconnect
    };
  }

  private _scheduleReconnect(): void {
    const delay = this.reconnect.nextDelay();
    if (delay === null) {
      this._setStatus("error");
      return;
    }
    this._setStatus("reconnecting");
    this.callbacks.onAttemptChange?.(this.reconnect.attemptCount);
    this.reconnectTimer = setTimeout(() => {
      if (!this.destroyed) this._openSocket();
    }, delay);
  }

  private _clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private _setStatus(status: ConnectionStatus): void {
    if (this.status === status) return;
    this.status = status;
    this.callbacks.onStatusChange(status);
  }
}

/** Build an absolute socket URL; empty configuration uses the current origin. */
export function buildWsUrl(apiBaseUrl: string, ticket: string): string {
  const url = new URL(apiBaseUrl || window.location.origin);
  if (url.username || url.password || !['http:', 'https:', 'ws:', 'wss:'].includes(url.protocol)) throw new Error('Invalid websocket origin');
  url.protocol = url.protocol === 'https:' || url.protocol === 'wss:' ? 'wss:' : 'ws:';
  if (window.location.protocol === 'https:' && url.protocol !== 'wss:') throw new Error('Insecure websocket origin');
  url.pathname = '/api/v1/realtime/ws';
  url.search = '';
  url.hash = '';
  url.searchParams.set('ticket', ticket);
  return url.toString();
}
