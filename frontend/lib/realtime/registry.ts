/**
 * Channel event handler registry.
 * Maps channel → set of handler callbacks.
 */
import type { RealtimeEvent } from "@/types/websocket";

export type EventHandler = (event: RealtimeEvent) => void;

export class HandlerRegistry {
  private handlers = new Map<string, Set<EventHandler>>();

  register(channel: string, handler: EventHandler): () => void {
    let set = this.handlers.get(channel);
    if (!set) {
      set = new Set();
      this.handlers.set(channel, set);
    }
    set.add(handler);
    return () => this.unregister(channel, handler);
  }

  unregister(channel: string, handler: EventHandler): void {
    this.handlers.get(channel)?.delete(handler);
  }

  dispatch(event: RealtimeEvent): void {
    this.handlers.get(event.channel)?.forEach((h) => h(event));
  }

  channels(): string[] {
    return [...this.handlers.keys()];
  }
}
