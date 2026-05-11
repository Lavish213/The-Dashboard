/**
 * WebSocket wire protocol types — mirrors backend realtime/protocol.py
 */

// ── Server → Client ──────────────────────────────────────────────────────────

export interface ConnectedAck {
  type: "connected";
  connection_id: string;
  server_time: string;
  user_id: string | null;
}

export interface PingMessage {
  type: "ping";
  timestamp: string;
}

export interface RealtimeEvent {
  type: "event";
  event_id: string;
  channel: string;
  event_type: string;
  payload: Record<string, unknown>;
  correlation_id: string | null;
  occurred_at: string;
}

export interface SubscribedAck {
  type: "subscribed";
  channel: string;
  last_event_id: string | null;
}

export interface UnsubscribedAck {
  type: "unsubscribed";
  channel: string;
}

export interface ReplayResponse {
  type: "replay";
  channel: string;
  events: RealtimeEvent[];
  has_more: boolean;
}

export interface RealtimeError {
  type: "error";
  code: string;
  message: string;
  channel: string | null;
}

export type ServerMessage =
  | ConnectedAck
  | PingMessage
  | RealtimeEvent
  | SubscribedAck
  | UnsubscribedAck
  | ReplayResponse
  | RealtimeError;

// ── Client → Server ──────────────────────────────────────────────────────────

export interface PongMessage {
  type: "pong";
}

export interface SubscribeRequest {
  type: "subscribe";
  channel: string;
  last_event_id?: string;
}

export interface UnsubscribeRequest {
  type: "unsubscribe";
  channel: string;
}

export interface ReplayRequest {
  type: "replay";
  channel: string;
  from_event_id?: string;
  limit?: number;
}

export type ClientMessage =
  | PongMessage
  | SubscribeRequest
  | UnsubscribeRequest
  | ReplayRequest;

// ── Channel names ─────────────────────────────────────────────────────────────

export type Channel =
  | "approvals"
  | "system"
  | `workflow:${string}`
  | `lead:${string}`
  | `user:${string}`;

// ── Connection state ──────────────────────────────────────────────────────────

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";
