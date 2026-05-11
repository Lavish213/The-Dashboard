/**
 * Native WebSocket client with:
 * - JWT token auth via ?token= query param
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
}

const PONG_RESPONSE = JSON.stringify({ type: "pong" });

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnect: ReconnectStrategy;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private destroyed = false;
  private status: ConnectionStatus = "disconnected";

  constructor(
    private readonly url: string,
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

  private _openSocket(): void {
    const ws = new WebSocket(this.url);
    this.ws = ws;

    ws.onopen = () => {
      this.reconnect.reset();
      this._setStatus("connected");
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

/** Build WebSocket URL from API base URL and JWT token. */
export function buildWsUrl(apiBaseUrl: string, token: string): string {
  const wsBase = apiBaseUrl.replace(/^http/, "ws");
  return `${wsBase}/api/v1/realtime/ws?token=${encodeURIComponent(token)}`;
}
