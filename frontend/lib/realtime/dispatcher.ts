/**
 * Message dispatcher — routes ServerMessages to the appropriate handlers.
 * Composed with EventDedup to skip duplicate events on reconnect.
 */
import type { ServerMessage } from "@/types/websocket";
import { EventDedup } from "./dedup";
import { HandlerRegistry } from "./registry";

export interface DispatcherCallbacks {
  onConnected: (connectionId: string) => void;
  onDisconnected: () => void;
  onSubscribed: (channel: string) => void;
  onUnsubscribed: (channel: string) => void;
  onError: (code: string, message: string, channel: string | null) => void;
}

export class MessageDispatcher {
  private dedup = new EventDedup();
  readonly registry = new HandlerRegistry();

  constructor(private readonly callbacks: DispatcherCallbacks) {}

  dispatch(msg: ServerMessage): void {
    switch (msg.type) {
      case "connected":
        this.callbacks.onConnected(msg.connection_id);
        break;

      case "ping":
        // ping handled at transport layer (WebSocketClient sends pong)
        break;

      case "event":
        if (this.dedup.add(msg.event_id)) {
          this.registry.dispatch(msg);
        }
        break;

      case "subscribed":
        this.callbacks.onSubscribed(msg.channel);
        break;

      case "unsubscribed":
        this.callbacks.onUnsubscribed(msg.channel);
        break;

      case "replay":
        for (const event of msg.events) {
          if (this.dedup.add(event.event_id)) {
            this.registry.dispatch(event);
          }
        }
        break;

      case "error":
        this.callbacks.onError(msg.code, msg.message, msg.channel);
        break;
    }
  }

  reset(): void {
    this.dedup = new EventDedup();
  }
}
